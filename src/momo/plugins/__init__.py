"""Scene plugins registry helper.

Scenes (会议、日程等) 在此挂载：实现 ``BasePlugin`` / ``Plugin``，
并在 ``load_plugins`` 中注册。当前为 stub，不加载任何插件。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from momo.plugins.base import BasePlugin, Plugin

if TYPE_CHECKING:
    from momo.tools.registry import ToolRegistry

__all__ = ["BasePlugin", "Plugin", "load_plugins"]


def load_plugins(registry: "ToolRegistry") -> list[str]:
    """Load scene plugins into ``registry``.

    Currently a no-op stub (no meeting plugin yet). Returns names loaded.
    """
    _ = registry  # reserved for future discovery
    return []
