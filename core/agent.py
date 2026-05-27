"""
Two-model agentic loop.

Qwen3 1.7B plans tool calls (structured JSON via Ollama format param).
Gemma3 1B produces the final spoken response with an emotion tag.
Tool results are appended as assistant role (no tool/system roles — speed optimization).
Loop is capped at MAX_TOOL_ITERATIONS to prevent runaway.
"""
import asyncio
import httpx
from datetime import datetime

import config
import core.ollama_client as ollama_client
import core.tools as tools
from core.schemas import ConversationResponse

_ERROR_RESPONSE = ConversationResponse(
    message="I'm having trouble thinking right now.",
    feeling="confused",
)


def _system_prompt() -> str:
    now = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    tool_list = tools.tool_descriptions()
    return (
        f"You are Lulu, a friendly desk companion. Current time: {now}.\n"
        f"You have access to these tools:\n{tool_list}\n"
        f"Call tools by returning JSON with function, describe, parameter fields. "
        f"When done, return function='finished'."
    )


def _conv_system_prompt() -> str:
    return (
        "You are Lulu, a friendly and concise desk companion. "
        "Respond naturally based on the conversation. "
        "Keep responses short and conversational. "
        "Return JSON with message (your spoken reply) and feeling (one of: happy, curious, neutral, sad, excited, confused)."
    )


async def run(message: str, history: list[dict]) -> ConversationResponse:
    loop = asyncio.get_event_loop()
    try:
        messages = [{"role": "system", "content": _system_prompt()}]
        for turn in history:
            if turn.get("role") in ("user", "assistant"):
                messages.append(turn)
        messages.append({"role": "user", "content": message})

        for _ in range(config.MAX_TOOL_ITERATIONS):
            tool_call = await loop.run_in_executor(None, ollama_client.call_agent, messages)
            if tool_call.function == "finished":
                break
            result = await loop.run_in_executor(
                None, tools.execute, tool_call.function, tool_call.parameter
            )
            messages.append({
                "role": "assistant",
                "content": f"[{tool_call.function}] {result}",
            })

        conv_messages = [{"role": "system", "content": _conv_system_prompt()}]
        conv_messages += [m for m in messages if m["role"] != "system"]

        return await loop.run_in_executor(None, ollama_client.call_conv, conv_messages)

    except (httpx.ConnectError, httpx.ConnectTimeout):
        return _ERROR_RESPONSE
    except Exception:
        return _ERROR_RESPONSE
