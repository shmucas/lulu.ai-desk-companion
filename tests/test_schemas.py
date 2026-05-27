import pytest
from pydantic import ValidationError
from core.schemas import ToolCall, ConversationResponse


def test_tool_call_valid():
    t = ToolCall(function="weather", describe="checking weather", parameter={"location": "Atlanta"})
    assert t.function == "weather"
    assert t.parameter == {"location": "Atlanta"}


def test_tool_call_finished_empty_parameter():
    t = ToolCall(function="finished", describe="done", parameter={})
    assert t.function == "finished"


def test_conversation_response_all_feelings():
    for feeling in ("happy", "curious", "neutral", "sad", "excited", "confused"):
        r = ConversationResponse(message="hi", feeling=feeling)
        assert r.feeling == feeling


def test_conversation_response_invalid_feeling():
    with pytest.raises(ValidationError):
        ConversationResponse(message="hi", feeling="angry")


def test_tool_call_json_schema_is_dict():
    schema = ToolCall.model_json_schema()
    assert isinstance(schema, dict)
    assert "properties" in schema
