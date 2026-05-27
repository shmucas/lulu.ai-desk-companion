from core.tools.weather import WeatherTool
from core.tools.web_search import WebSearchTool
from core.tools.time_tool import TimeTool

_REGISTRY: dict[str, object] = {}


def _register(*tool_classes):
    for cls in tool_classes:
        t = cls()
        _REGISTRY[t.name] = t


_register(WeatherTool, WebSearchTool, TimeTool)


def tool_descriptions() -> str:
    lines = []
    for t in _REGISTRY.values():
        lines.append(f'- {t.name}: {t.description}. parameter schema: {t.parameter_spec}')
    return "\n".join(lines)


def execute(name: str, parameter: dict) -> str:
    tool = _REGISTRY.get(name)
    if tool is None:
        return f"Unknown tool: {name!r}. Available: {', '.join(_REGISTRY)}"
    try:
        return tool.execute(**parameter)
    except Exception as e:
        return f"Tool {name!r} failed: {e}"
