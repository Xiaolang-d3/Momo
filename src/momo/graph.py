"""LangGraph agent kernel: reason → decide → confirm (HITL) → execute (+ retry/block)."""

from __future__ import annotations

from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from momo.demo_plan import build_demo_plan
from momo.nodes import make_nodes
from momo.provider import ModelProvider
from momo.state import AgentState
from momo.tools.registry import ToolRegistry, get_default_registry


def _route_after_decide(state: AgentState) -> Literal["confirm", "__end__"]:
    if state.get("status") == "done" or not state.get("pending_action"):
        return "__end__"
    return "confirm"


def _route_after_confirm(state: AgentState) -> Literal["execute", "__end__"]:
    if state.get("status") == "cancelled":
        return "__end__"
    return "execute"


def _route_after_execute(state: AgentState) -> Literal["execute", "decide", "__end__"]:
    status = state.get("status")
    if status in ("cancelled", "error", "done", "blocked"):
        return "__end__"
    # 仍有 pending 且刚记了一次重试 → 再跑 execute
    pending = state.get("pending_action")
    retries = int(state.get("tool_retries") or 0)
    if pending and retries > 0 and status == "running":
        return "execute"
    plan = state.get("plan") or []
    step_index = int(state.get("step_index") or 0)
    if step_index >= len(plan):
        return "__end__"
    return "decide"


def build_graph(
    registry: ToolRegistry | None = None,
    demo: bool = True,
    checkpointer: MemorySaver | None = None,
    provider: ModelProvider | None = None,
    max_tool_retries: int = 1,
):
    """Compile the agent StateGraph with HITL interrupt + retry/block."""
    registry = registry or get_default_registry()
    reason_node, decide_node, confirm_node, execute_node = make_nodes(
        registry,
        demo=demo,
        provider=provider,
        max_tool_retries=max_tool_retries,
    )

    g = StateGraph(AgentState)
    g.add_node("reason", reason_node)
    g.add_node("decide", decide_node)
    g.add_node("confirm", confirm_node)
    g.add_node("execute", execute_node)

    g.add_edge(START, "reason")
    g.add_edge("reason", "decide")
    g.add_conditional_edges(
        "decide",
        _route_after_decide,
        {"confirm": "confirm", "__end__": END},
    )
    g.add_conditional_edges(
        "confirm",
        _route_after_confirm,
        {"execute": "execute", "__end__": END},
    )
    g.add_conditional_edges(
        "execute",
        _route_after_execute,
        {"execute": "execute", "decide": "decide", "__end__": END},
    )

    saver = checkpointer if checkpointer is not None else MemorySaver()
    return g.compile(checkpointer=saver)


__all__ = ["build_graph", "build_demo_plan", "Command"]
