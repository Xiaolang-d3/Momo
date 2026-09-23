"""Deterministic offline provider — no network."""

from __future__ import annotations

from momo.provider.base import ModelProvider


class DemoProvider(ModelProvider):
    """Fixed replies for offline / --demo runs."""

    name = "demo"

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        preview = (prompt or "").strip().replace("\n", " ")
        if len(preview) > 80:
            preview = preview[:77] + "..."
        return (
            "[demo-provider] 离线确定性回复。"
            f" 收到 prompt 长度={len(prompt or '')}"
            + (f"；摘要={preview}" if preview else "")
        )
