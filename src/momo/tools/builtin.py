"""Built-in example tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from momo.tools.registry import ToolRegistry


def echo(text: str = "") -> str:
    """Return the input text unchanged."""
    return str(text)


def add(a: float = 0, b: float = 0) -> str:
    """Add two numbers and return a readable result."""
    result = float(a) + float(b)
    if result.is_integer():
        result_s = str(int(result))
    else:
        result_s = str(result)
    return f"{a} + {b} = {result_s}"


def propose_action(action: str = "", detail: str = "") -> str:
    """Sensitive action that always requires human confirmation before run."""
    return f"已执行提议动作: {action}" + (f" ({detail})" if detail else "")


def register_builtin_tools(registry: "ToolRegistry") -> None:
    registry.register(
        "echo",
        echo,
        description="回显输入文本。参数: text (str)",
        requires_confirmation=False,
    )
    registry.register(
        "add",
        add,
        description="将两个数字相加。参数: a (number), b (number)",
        requires_confirmation=False,
    )
    registry.register(
        "propose_action",
        propose_action,
        description="提议执行敏感动作（需人工确认）。参数: action (str), detail (str, 可选)",
        requires_confirmation=True,
    )
