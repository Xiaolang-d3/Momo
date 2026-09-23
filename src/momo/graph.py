"""LangGraph agent kernel: reason → decide → confirm (HITL) → execute (+ retry/block)."""

from __future__ import annotations

import json
from typing import Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from momo.provider import ModelProvider, get_provider
from momo.state import AgentState
from momo.tools.builtin import reset_flaky_counters
from momo.tools.registry import ToolRegistry, get_default_registry


# ---------------------------------------------------------------------------
# Deterministic demo planner (no LLM / API key required)
# ---------------------------------------------------------------------------

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
