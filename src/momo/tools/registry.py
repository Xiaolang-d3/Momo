"""Plugin-style tool registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


ToolFn = Callable[..., Any]


@dataclass
class ToolSpec:
    name: str
    fn: ToolFn
    description: str
    requires_confirmation: bool = False


class ToolRegistry:
    """Register and look up tools by name."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(
        self,
        name: str,
        fn: ToolFn,
        description: str,
        requires_confirmation: bool = False,
    ) -> None:
        if not name or not callable(fn):
            raise ValueError("name and callable fn are required")
        self._tools[name] = ToolSpec(
            name=name,
            fn=fn,
            description=description,
            requires_confirmation=requires_confirmation,
        )

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def list_tools(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def descriptions(self) -> str:
        lines = []
        for t in self._tools.values():
            flag = " [需确认]" if t.requires_confirmation else ""
            lines.append(f"- {t.name}{flag}: {t.description}")
        return "\n".join(lines)

    def call(self, name: str, **kwargs: Any) -> Any:
        spec = self.get(name)
        if spec is None:
            raise KeyError(f"unknown tool: {name}")
        return spec.fn(**kwargs)


_default: ToolRegistry | None = None


def get_default_registry() -> ToolRegistry:
    global _default
    if _default is None:
        from momo.plugins import load_plugins
        from momo.tools.builtin import register_builtin_tools

        _default = ToolRegistry()
        register_builtin_tools(_default)
        load_plugins(_default)  # stub: currently no-op
    return _default
