"""
Two-model agentic pipeline.

Qwen3 1.7B plans tool calls (structured JSON) and, on "finished", writes a
natural-language summary of what it learned. Gemma3 1B never sees raw tool
output or intermediate tool-call turns - only that summary - since the small
conversational model gets confused by anything that isn't a clean
user/assistant turn.
Loop is capped at MAX_TOOL_ITERATIONS.
"""
import asyncio
import traceback
from datetime import datetime

import httpx
import memory_store
import ollama_client
import tools
from config import MAX_TOOL_ITERATIONS
from schemas import ConversationResponse

_ERROR_RESPONSE = ConversationResponse(
    message="I'm having trouble thinking right now.",
    feeling="confused",
)


def _memory_block() -> str:
    known = memory_store.facts()
    if not known:
        return ""
    listed = "\n".join(f"- {fact}" for fact in known[-15:])
    return f"\nThings you remember about the user:\n{listed}\n"


def _agent_system_prompt() -> str:
    now = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    return (
        f"You are Lulu, a friendly desk companion. Current time: {now}.\n"
        f"You have access to these tools:\n{tools.tool_descriptions()}\n"
        f"{_memory_block()}"
        f"Most messages (greetings, chit-chat, opinions, anything you already know) need "
        f"NO tool at all. Only call a tool when the user is explicitly asking for something "
        f"only a tool can provide (current weather, a web search, the exact time, a joke, "
        f"setting a timer or reminder, or remembering a fact for later). "
        f"If no tool is needed, immediately return function='finished' with an empty parameter "
        f"object - never invent or fabricate a tool result yourself.\n"
        f"Call tools by returning JSON with function, describe, parameter fields. "
        f"When done, return function='finished'."
    )


def _conv_system_prompt(context: str | None = None) -> str:
    prompt = (
        "You are Lulu, a friendly and concise desk companion. "
        "Respond naturally based on the conversation, in plain spoken text - "
        "no JSON, no markdown, just what you'd say out loud. "
        "Keep responses short and conversational."
        + _memory_block()
    )
    if context:
        prompt += f"\n\nUse this information to answer the user's question: {context}"
    return prompt


async def run_pipeline(transcript: str, history: list[dict]) -> ConversationResponse:
    loop = asyncio.get_event_loop()
    try:
        messages = [{"role": "system", "content": _agent_system_prompt()}]
        for turn in history:
            if turn.get("role") in ("user", "assistant"):
                messages.append(turn)
        messages.append({"role": "user", "content": transcript})
        pre_tool_loop_len = len(messages)  # history + current transcript, before any tool trace

        last_call = None
        last_result = None
        summary = None
        fired_side_effects: set[str] = set()
        for _ in range(MAX_TOOL_ITERATIONS):
            tool_call = await loop.run_in_executor(None, ollama_client.call_agent, messages)
            if tool_call.function == "finished":
                summary = tool_call.describe or None
                break
            call_key = (tool_call.function, tuple(sorted(tool_call.parameter.items())))
            if call_key == last_call:
                # Agent repeated an identical call - it already has this result, stop looping.
                break
            if tool_call.function in fired_side_effects:
                # Small models sometimes re-call a side-effect tool with slightly
                # different params (two timers for one request). Once is enough.
                break
            if tools.has_side_effects(tool_call.function):
                fired_side_effects.add(tool_call.function)
            last_call = call_key
            last_result = await loop.run_in_executor(
                None, tools.execute, tool_call.function, tool_call.parameter
            )
            messages.append({
                "role": "assistant",
                "content": f"[{tool_call.function}] {last_result}",
            })

        # Gemma3 gets confused by raw "[tool] ..." telemetry, and by a message
        # list that ends on an assistant turn with no following user turn -
        # so tool findings go into the system prompt as context instead, and
        # the conversation ends on the user's actual question as normal.
        conv_messages = [{"role": "system", "content": _conv_system_prompt(summary or last_result)}]
        conv_messages += messages[1:pre_tool_loop_len]  # skip system, keep history + transcript

        return await loop.run_in_executor(None, ollama_client.call_conv, conv_messages)

    except (httpx.ConnectError, httpx.ConnectTimeout):
        print("[llm] cannot reach Ollama - is it running? (ollama serve)", flush=True)
        return _ERROR_RESPONSE
    except Exception:
        print("[llm] pipeline error:\n" + traceback.format_exc(), flush=True)
        return _ERROR_RESPONSE
