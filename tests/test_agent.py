import json
import pytest
import httpx
from unittest.mock import patch, MagicMock

from core.schemas import ToolCall, ConversationResponse


def _tool_call(function="finished", describe="done", parameter=None):
    return ToolCall(function=function, describe=describe, parameter=parameter or {})


def _conv_response(message="ok", feeling="neutral"):
    return ConversationResponse(message=message, feeling=feeling)


@pytest.mark.asyncio
async def test_run_finished_on_first_call():
    with (
        patch("core.ollama_client.call_agent", return_value=_tool_call("finished")),
        patch("core.ollama_client.call_conv", return_value=_conv_response("Done!")),
    ):
        from core import agent
        result = await agent.run("hi", [])
    assert result.message == "Done!"


@pytest.mark.asyncio
async def test_run_one_tool_call_then_finished():
    calls = [_tool_call("get_time"), _tool_call("finished")]
    call_iter = iter(calls)

    with (
        patch("core.ollama_client.call_agent", side_effect=lambda _: next(call_iter)),
        patch("core.ollama_client.call_conv", return_value=_conv_response("It is noon.")),
        patch("core.tools.execute", return_value="Tuesday, May 27, 2026 at 12:00 PM"),
    ):
        from core import agent
        result = await agent.run("what time is it?", [])
    assert result.message == "It is noon."


@pytest.mark.asyncio
async def test_run_loop_cap_still_returns_response():
    """Hits MAX_TOOL_ITERATIONS without finished() — must still return a response."""
    import config
    always_tool = _tool_call("get_time")

    with (
        patch("core.ollama_client.call_agent", return_value=always_tool),
        patch("core.ollama_client.call_conv", return_value=_conv_response("capped")),
        patch("core.tools.execute", return_value="noon"),
        patch.object(config, "MAX_TOOL_ITERATIONS", 3),
    ):
        from core import agent
        result = await agent.run("what time is it?", [])
    assert result.message == "capped"


@pytest.mark.asyncio
async def test_run_unknown_tool_continues_without_crash():
    calls = [_tool_call("send_email", parameter={"to": "x"}), _tool_call("finished")]
    call_iter = iter(calls)

    with (
        patch("core.ollama_client.call_agent", side_effect=lambda _: next(call_iter)),
        patch("core.ollama_client.call_conv", return_value=_conv_response("handled")),
    ):
        from core import agent
        result = await agent.run("send an email", [])
    assert result.message == "handled"


@pytest.mark.asyncio
async def test_run_ollama_unreachable_returns_error_response():
    with patch("core.ollama_client.call_agent", side_effect=httpx.ConnectError("refused")):
        from core import agent
        result = await agent.run("hi", [])
    assert result.feeling == "confused"
    assert "trouble" in result.message
