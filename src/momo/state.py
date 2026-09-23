"""Agent graph state definition."""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph.message import add_messages


class PendingAction(TypedDict, total=False):
    tool: str
    args: dict[str, Any]
    reason: str


class AgentState(TypedDict, total=False):
    """Shared state flowing through the agent graph."""

    messages: Annotated[list, add_messages]
    task: str
    plan: list[dict[str, Any]]
    step_index: int
    pending_action: PendingAction | None
    last_tool_result: str | None
    status: Literal["running", "awaiting_confirm", "done", "cancelled", "error"]
    history: list[str]
