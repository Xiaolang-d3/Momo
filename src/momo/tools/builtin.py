"""Built-in example tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from momo.tools.registry import ToolRegistry

# 模块级计数：演示「失败一次后成功」的重试路径
_flaky_calls: dict[str, int] = {}


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


def flaky_once(label: str = "demo", fail_times: int = 1) -> str:
    """Fail the first ``fail_times`` calls, then succeed (proves retry).

    Uses a module-level counter keyed by ``label``. Reset between processes.
    """
    key = str(label or "demo")
    n = int(fail_times) if fail_times is not None else 1
    if n < 0:
        n = 0
    count = _flaky_calls.get(key, 0)
    _flaky_calls[key] = count + 1
    if count < n:
        raise RuntimeError(
            f"flaky_once[{key}]: 故意失败 "
            f"(第 {count + 1}/{n} 次，用于演示重试)"
        )
    return f"flaky_once[{key}]: 第 {count + 1} 次调用成功（已度过失败窗口）"


def always_fail(reason: str = "故意永久失败，用于演示 blocked") -> str:
    """Always raise — after retries the kernel should set status=blocked."""
    raise RuntimeError(str(reason or "always_fail"))


def reset_flaky_counters() -> None:
    """Test/demo helper: clear flaky_once counters."""
    _flaky_calls.clear()


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
    registry.register(
        "flaky_once",
        flaky_once,
        description=(
            "前 N 次调用失败、之后成功（演示重试）。"
            "参数: label (str), fail_times (int, 默认 1)"
        ),
        requires_confirmation=False,
    )
    registry.register(
        "always_fail",
        always_fail,
        description="始终失败（演示重试耗尽 → blocked）。参数: reason (str, 可选)",
        requires_confirmation=False,
    )

    from momo.tools.library import register_library_tools

    register_library_tools(registry)
