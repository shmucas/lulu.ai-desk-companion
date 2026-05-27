import pytest
from core.tools import execute, tool_descriptions
from core.tools.time_tool import TimeTool


# ── Unit tests ──────────────────────────────────────────────────────────────

def test_tool_descriptions_lists_all_tools():
    desc = tool_descriptions()
    assert "weather" in desc
    assert "web_search" in desc
    assert "get_time" in desc


def test_execute_unknown_tool_returns_string_not_exception():
    result = execute("nonexistent_tool", {})
    assert "Unknown tool" in result
    assert "nonexistent_tool" in result


def test_time_tool_returns_day_and_date():
    result = TimeTool().execute()
    # Should contain a day name and a year
    days = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
    assert any(day in result for day in days)
    assert "2026" in result or "2025" in result  # year present


# ── Integration tests (require network) ─────────────────────────────────────

@pytest.mark.integration
def test_weather_happy_path():
    result = execute("weather", {"location": "Atlanta, GA"})
    assert "Atlanta" in result or "°F" in result


@pytest.mark.integration
def test_weather_bad_location_returns_error_string():
    result = execute("weather", {"location": "ZZZNOPLACEEXISTS123"})
    assert "Could not find" in result or "fetch" in result.lower()


@pytest.mark.integration
def test_web_search_happy_path():
    result = execute("web_search", {"query": "python programming language"})
    assert len(result) > 20  # got something back
    assert result != "No results found."


@pytest.mark.integration
def test_web_search_empty_query_returns_string():
    result = execute("web_search", {"query": "xzxzxzxzxzxz_unlikely_query_9999"})
    # Either no results or a string — must not crash
    assert isinstance(result, str)
