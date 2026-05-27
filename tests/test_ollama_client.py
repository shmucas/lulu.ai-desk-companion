import json
import pytest
import httpx
from unittest.mock import patch, MagicMock

from core.schemas import ToolCall, ConversationResponse


def _mock_response(content: dict):
    mock = MagicMock()
    mock.json.return_value = {"message": {"content": json.dumps(content)}}
    mock.raise_for_status.return_value = None
    return mock


def test_call_agent_happy_path():
    payload = {"function": "weather", "describe": "checking", "parameter": {"location": "Atlanta"}}
    with patch("httpx.post", return_value=_mock_response(payload)):
        from core import ollama_client
        result = ollama_client.call_agent([{"role": "user", "content": "weather?"}])
    assert isinstance(result, ToolCall)
    assert result.function == "weather"


def test_call_agent_ollama_unreachable():
    with patch("httpx.post", side_effect=httpx.ConnectError("refused")):
        from core import ollama_client
        import pytest
        with pytest.raises(httpx.ConnectError):
            ollama_client.call_agent([{"role": "user", "content": "hi"}])


def test_call_agent_malformed_json_returns_finished():
    mock = MagicMock()
    mock.json.return_value = {"message": {"content": "not json at all"}}
    mock.raise_for_status.return_value = None
    with patch("httpx.post", return_value=mock):
        from core import ollama_client
        result = ollama_client.call_agent([{"role": "user", "content": "hi"}])
    assert result.function == "finished"


def test_call_conv_happy_path():
    payload = {"message": "The weather is nice!", "feeling": "happy"}
    with patch("httpx.post", return_value=_mock_response(payload)):
        from core import ollama_client
        result = ollama_client.call_conv([{"role": "user", "content": "hi"}])
    assert isinstance(result, ConversationResponse)
    assert result.feeling == "happy"


def test_call_conv_malformed_json_returns_error_response():
    mock = MagicMock()
    mock.json.return_value = {"message": {"content": "bad json"}}
    mock.raise_for_status.return_value = None
    with patch("httpx.post", return_value=mock):
        from core import ollama_client
        result = ollama_client.call_conv([{"role": "user", "content": "hi"}])
    assert result.feeling == "confused"
    assert "trouble" in result.message
