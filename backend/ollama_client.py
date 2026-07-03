import json
import re
import traceback
from typing import get_args

import httpx
from config import OLLAMA_HOST, AGENT_MODEL, CONV_MODEL
from schemas import ToolCall, ConversationResponse

_URL = f"{OLLAMA_HOST}/api/chat"
_TIMEOUT = 60.0

# Piper reads text literally and mangles emoji into garbled sounds - strip
# before the reply is spoken (or classified).
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # symbols, pictographs, emoticons, supplemental
    "\U00002600-\U000027BF"  # misc symbols, dingbats
    "\U0001F1E6-\U0001F1FF"  # regional indicators (flags)
    "\U00002190-\U000021FF"  # arrows
    "\U00002300-\U000023FF"  # misc technical (stopwatch, hourglass, alarm clock)
    "\U00002B00-\U00002BFF"  # misc symbols and arrows (stars)
    "️"                 # variation selector (emoji presentation)
    "]+"
)


def _strip_emoji(text: str) -> str:
    return _EMOJI_RE.sub("", text).strip()

_ERROR_RESPONSE = ConversationResponse(
    message="I'm having trouble thinking right now.",
    feeling="confused",
)

_VALID_FEELINGS = set(get_args(ConversationResponse.model_fields["feeling"].annotation))
_FEELING_SCHEMA = {
    "type": "object",
    "properties": {"feeling": {"type": "string", "enum": sorted(_VALID_FEELINGS)}},
    "required": ["feeling"],
}


def call_agent(messages: list[dict]) -> ToolCall:
    try:
        resp = httpx.post(
            _URL,
            json={
                "model": AGENT_MODEL,
                "messages": messages,
                "stream": False,
                "format": ToolCall.model_json_schema(),
                "think": False,
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
    # Forcing the full {message, feeling} JSON schema on a 1B model makes it
    # collapse to generic filler ("Happy") instead of using the conversation
    # context - the constrained decoding competes with actually reasoning
    # about content. So the reply is generated unconstrained (reliable), and
    # "feeling" is classified in a cheap second call, where a one-word
    # classification is trivial even under a schema constraint.
    try:
        resp = httpx.post(
            _URL,
            json={
                "model": CONV_MODEL,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.7},
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        reply = _strip_emoji(resp.json()["message"]["content"])
        return ConversationResponse(message=reply, feeling=_classify_feeling(reply))
    except (httpx.ConnectError, httpx.ConnectTimeout):
        raise
    except Exception:
        print(f"[ollama] conv call failed ({CONV_MODEL}):\n" + traceback.format_exc(), flush=True)
        return _ERROR_RESPONSE


def _classify_feeling(reply: str) -> str:
    try:
        resp = httpx.post(
            _URL,
            json={
                "model": CONV_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "Classify the emotional tone of this assistant reply.",
                    },
                    {"role": "user", "content": reply},
                ],
                "stream": False,
                "format": _FEELING_SCHEMA,
                "options": {"temperature": 0},
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        feeling = json.loads(resp.json()["message"]["content"]).get("feeling")
        return feeling if feeling in _VALID_FEELINGS else "neutral"
    except Exception:
        return "neutral"


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
