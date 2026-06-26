from tools.weather import WeatherTool
from tools.search import WebSearchTool
from tools.time_tool import TimeTool

_REGISTRY: dict[str, object] = {}


def _register(*tool_classes):
    for cls in tool_classes:
        t = cls()
        _REGISTRY[t.name] = t


_register(WeatherTool, WebSearchTool, TimeTool)


def tool_descriptions() -> str:
    return "\n".join(
        f"- {t.name}: {t.description}. parameter schema: {t.parameter_spec}"
        for t in _REGISTRY.values()
    )


def execute(name: str, parameter: dict) -> str:
    tool = _REGISTRY.get(name)
    if tool is None:
        return f"Unknown tool: {name!r}. Available: {', '.join(_REGISTRY)}"
    try:
        return tool.execute(**parameter)
    except Exception as e:
        return f"Tool {name!r} failed: {e}"
