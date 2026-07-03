from tools.weather import WeatherTool
from tools.search import WebSearchTool
from tools.time_tool import TimeTool
from tools.joke import JokeTool
from tools.remember import RememberTool
from tools.timer import TimerTool, ReminderTool

_REGISTRY: dict[str, object] = {}


def _register(*tool_classes):
    for cls in tool_classes:
        t = cls()
        _REGISTRY[t.name] = t


_register(WeatherTool, WebSearchTool, TimeTool, JokeTool,
          RememberTool, TimerTool, ReminderTool)


def has_side_effects(name: str) -> bool:
    """True for tools that must not run twice in one request (timers etc.)."""
    return bool(getattr(_REGISTRY.get(name), "side_effect", False))


def tool_descriptions() -> str:
    return "\n".join(
        f"- {t.name}: {t.description}. parameter schema: {t.parameter_spec}"
        for t in _REGISTRY.values()
    )


def execute(name: str, parameter: dict) -> str:
    tool = _REGISTRY.get(name)
    if tool is None:
        return f"Unknown tool: {name!r}. Available: {', '.join(_REGISTRY)}"
    # The agent model sometimes hallucinates parameter names outside the
    # declared schema - drop anything it doesn't ask for instead of erroring.
    known = tool.parameter_spec.keys()
    parameter = {k: v for k, v in parameter.items() if k in known}
    try:
        return tool.execute(**parameter)
    except Exception as e:
        return f"Tool {name!r} failed: {e}"
