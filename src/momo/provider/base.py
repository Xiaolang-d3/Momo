"""Abstract model provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ModelProvider(ABC):
    """Minimal completion API for the agent kernel."""

    name: str = "base"

    @abstractmethod
    def complete(self, prompt: str, *, system: str | None = None) -> str:
        """Return a text completion for ``prompt``."""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
