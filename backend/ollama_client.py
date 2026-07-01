import traceback

import httpx
from config import OLLAMA_HOST, AGENT_MODEL, CONV_MODEL
from schemas import ToolCall, ConversationResponse

_URL = f"{OLLAMA_HOST}/api/chat"
_TIMEOUT = 60.0

_ERROR_RESPONSE = ConversationResponse(
    message="I'm having trouble thinking right now.",
    feeling="confused",
)


def call_agent(messages: list[dict]) -> ToolCall:
    try:
        resp = httpx.post(
            _URL,
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
        return ToolCall.model_validate_json(resp.json()["message"]["content"])
    except (httpx.ConnectError, httpx.ConnectTimeout):
        raise
    except Exception:
        print(f"[ollama] agent call failed ({AGENT_MODEL}):\n" + traceback.format_exc(), flush=True)
        return ToolCall(function="finished", describe="error", parameter={})


def call_conv(messages: list[dict]) -> ConversationResponse:
    try:
        resp = httpx.post(
            _URL,
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
        return ConversationResponse.model_validate_json(resp.json()["message"]["content"])
    except (httpx.ConnectError, httpx.ConnectTimeout):
        raise
    except Exception:
        print(f"[ollama] conv call failed ({CONV_MODEL}):\n" + traceback.format_exc(), flush=True)
        return _ERROR_RESPONSE


def warmup() -> None:
    for model in (AGENT_MODEL, CONV_MODEL):
        try:
            httpx.post(
                _URL,
                json={"model": model, "messages": [{"role": "user", "content": "hi"}], "stream": False},
                timeout=30.0,
            )
        except Exception:
            pass
