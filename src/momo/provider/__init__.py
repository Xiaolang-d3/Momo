"""Model provider factory and re-exports."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from momo.provider.base import ModelProvider
from momo.provider.demo import DemoProvider
from momo.provider.ollama import OllamaProvider
from momo.provider.openai_compat import OpenAICompatibleProvider

if TYPE_CHECKING:
    pass

__all__ = [
    "ModelProvider",
    "DemoProvider",
    "OpenAICompatibleProvider",
    "OllamaProvider",
    "get_provider",
]


def get_provider(name: str | None = None) -> ModelProvider:
    """Return a provider by name or ``MOMO_PROVIDER`` env (default: demo)."""
    key = (name or os.environ.get("MOMO_PROVIDER") or "demo").strip().lower()
    if key in ("demo", "deterministic", "offline"):
        return DemoProvider()
    if key in ("openai", "openai_compatible", "openai-compatible"):
        return OpenAICompatibleProvider()
    if key in ("ollama",):
        return OllamaProvider()
    # Unknown → safe offline fallback
    return DemoProvider()
