"""Plugin contract for scene capabilities (meeting etc. — implement later)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from momo.tools.registry import ToolRegistry


@runtime_checkable
class Plugin(Protocol):
    """Structural contract: scenes expose a name and register tools."""

    @property
    def name(self) -> str: ...

    def tools(self) -> list[dict]:
        """Optional tool specs metadata (name/description/...)."""
        ...

    def register(self, registry: "ToolRegistry") -> None:
        """Hook tools into the shared registry."""
        ...


class BasePlugin(ABC):
    """ABC helpers for concrete plugins (meeting plugin comes next phase)."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    def tools(self) -> list[dict]:
        return []

    @abstractmethod
    def register(self, registry: "ToolRegistry") -> None: ...
