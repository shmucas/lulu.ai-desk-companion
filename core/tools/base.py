from typing import Protocol, runtime_checkable


@runtime_checkable
class Tool(Protocol):
    name: str
    description: str
    parameter_spec: dict

    def execute(self, **kwargs) -> str: ...
