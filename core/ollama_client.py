"""
Thin HTTP wrapper around Ollama.
call_agent → Qwen3 with structured ToolCall output
call_conv  → Gemma3 with structured ConversationResponse output
Both return typed Pydantic models; errors return a safe fallback ConversationResponse.
"""
import httpx
from config import OLLAMA_HOST, AGENT_MODEL, CONV_MODEL
from core.schemas import ToolCall, ConversationResponse

_AGENT_URL = f"{OLLAMA_HOST}/api/chat"
_TIMEOUT = 60.0

_ERROR_RESPONSE = ConversationResponse(
    message="I'm having trouble thinking right now.",
    feeling="confused",
)


def call_agent(messages: list[dict]) -> ToolCall:
    try:
        resp = httpx.post(
            _AGENT_URL,
            json={
                "model": AGENT_MODEL,
                "messages": messages,
                "stream": False,
                "format": ToolCall.model_json_schema(),
                "options": {"temperature": 0},
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        return ToolCall.model_validate_json(content)
    except (httpx.ConnectError, httpx.ConnectTimeout):
        raise
    except Exception:
        return ToolCall(function="finished", describe="error", parameter={})


def call_conv(messages: list[dict]) -> ConversationResponse:
    try:
        resp = httpx.post(
            _AGENT_URL,
            json={
                "model": CONV_MODEL,
                "messages": messages,
                "stream": False,
                "format": ConversationResponse.model_json_schema(),
                "options": {"temperature": 0.7},
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        return ConversationResponse.model_validate_json(content)
    except (httpx.ConnectError, httpx.ConnectTimeout):
        raise
    except Exception:
        return _ERROR_RESPONSE


def warmup() -> None:
    """Pre-load both models into Ollama RAM. Called on FastAPI startup."""
    for model in (AGENT_MODEL, CONV_MODEL):
        try:
            httpx.post(
                _AGENT_URL,
                json={"model": model, "messages": [{"role": "user", "content": "hi"}], "stream": False},
                timeout=30.0,
            )
        except Exception:
            pass
