"""Deterministic demo planner + optional provider plan attempt."""

from __future__ import annotations

from typing import Any

from momo.provider import ModelProvider


def build_demo_plan(task: str) -> list[dict[str, Any]]:
    """Fixed multi-step plan: library tools + HITL + flaky retry path."""
    task = (task or "").strip() or "演示：库检索、HITL 确认与失败重试"
    return [
        {
            "tool": "echo",
            "args": {"text": f"收到任务: {task}"},
            "reason": "先回显任务内容",
        },
        {
            "tool": "search_library",
            "args": {"query": "HITL"},
            "reason": "在内存文档库中搜索 HITL 相关条目",
        },
        {
            "tool": "get_library_context",
            "args": {"doc_id": "momo-kernel"},
            "reason": "取回底座文档上下文",
        },
        {
            "tool": "add",
            "args": {"a": 19, "b": 23},
            "reason": "做一次简单计算",
        },
        {
            "tool": "flaky_once",
            "args": {"label": "demo-retry", "fail_times": 1},
            "reason": "故意失败一次，验证内核重试后成功",
        },
        {
            "tool": "propose_action",
            "args": {
                "action": "写入演示日志",
                "detail": "仅原型演示，不会真正写文件",
            },
            "reason": "敏感操作，需要人工确认",
        },
        {
            "tool": "echo",
            "args": {"text": "多步工具 + HITL + 重试演示完成"},
            "reason": "收尾回显",
        },
    ]


def try_provider_plan(
    provider: ModelProvider,
    task: str,
    history: list[str],
) -> list[dict[str, Any]] | None:
    """Ask provider for a plan. DemoProvider / failures → None (caller falls back)."""
    if getattr(provider, "name", "") == "demo":
        history.append("[reason] provider=demo，跳过 LLM，使用演示规划器")
        return None
    system = (
        "你是 Momo Agent 规划器。只输出 JSON 数组，每项含 tool/args/reason。"
        "可用工具见用户消息。不要解释。"
    )
    prompt = (
        f"任务: {task}\n"
        "请给出最多 6 步的工具调用计划（JSON 数组）。"
        "若无法规划，输出 []。"
    )
    try:
        raw = provider.complete(prompt, system=system)
        history.append(
            f"[reason] provider={provider.name} 已调用，回复长度={len(raw)}"
        )
        history.append(
            "[reason] 内核暂用演示规划器落地执行（provider 输出已记录，后续可解析）"
        )
        return None
    except Exception as exc:  # noqa: BLE001
        history.append(f"[reason] provider={provider.name} 失败: {exc}；回退演示规划器")
        return None
