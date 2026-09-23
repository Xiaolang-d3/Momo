"""Agent graph state definition."""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph.message import add_messages


StatusLiteral = Literal[
    "running",
    "awaiting_confirm",
    "done",
    "cancelled",
    "error",
    "blocked",
]


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
    status: StatusLiteral
    history: list[str]
    # 工具失败后的重试计数（当前步骤）；成功或换步时清零
    tool_retries: int
    # 达到重试上限后阻塞时的原因说明
    block_reason: str | None
    # 本图允许的最大额外重试次数（默认 1 = 失败后再试一次）
    max_tool_retries: int

