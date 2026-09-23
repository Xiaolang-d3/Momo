"""LangGraph agent: plan → decide → (HITL) → execute → continue."""

from __future__ import annotations

import json
from typing import Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from momo.state import AgentState
from momo.tools.registry import ToolRegistry, get_default_registry


# ---------------------------------------------------------------------------
# Deterministic demo planner (no LLM / API key required)
# ---------------------------------------------------------------------------

def build_demo_plan(task: str) -> list[dict[str, Any]]:
    """Build a fixed multi-step plan that exercises tools + HITL."""
    task = (task or "").strip() or "演示：回显、加法与需确认动作"
    return [
        {
            "tool": "echo",
            "args": {"text": f"收到任务: {task}"},
            "reason": "先回显任务内容",
        },
        {
            "tool": "add",
            "args": {"a": 19, "b": 23},
            "reason": "做一次简单计算",
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
            "args": {"text": "多步工具调用与 HITL 演示完成"},
            "reason": "收尾回显",
        },
    ]


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

def make_nodes(registry: ToolRegistry, demo: bool = True):
    def reason_node(state: AgentState) -> dict[str, Any]:
        """Think / plan next steps."""
        history = list(state.get("history") or [])
        plan = list(state.get("plan") or [])
        step_index = int(state.get("step_index") or 0)

        if not plan:
            task = state.get("task") or ""
            if demo:
                plan = build_demo_plan(task)
                history.append(f"[reason] 使用离线演示规划器，共 {len(plan)} 步")
            else:
                # Placeholder for future LLM planning; fall back to demo plan
                plan = build_demo_plan(task)
                history.append(
                    "[reason] 未配置 LLM，回退到演示规划器"
                )

        return {
            "plan": plan,
            "step_index": step_index,
            "status": "running",
            "history": history,
        }

    def decide_node(state: AgentState) -> dict[str, Any]:
        """Decide whether a tool is needed for the current step."""
        history = list(state.get("history") or [])
        plan = state.get("plan") or []
        step_index = int(state.get("step_index") or 0)

        if step_index >= len(plan):
            history.append("[decide] 计划已全部完成")
            return {
                "pending_action": None,
                "status": "done",
                "history": history,
            }

        step = plan[step_index]
        tool_name = step.get("tool", "")
        args = dict(step.get("args") or {})
        reason = step.get("reason", "")
        history.append(
            f"[decide] 步骤 {step_index + 1}/{len(plan)} → tool={tool_name} ({reason})"
        )
        return {
            "pending_action": {
                "tool": tool_name,
                "args": args,
                "reason": reason,
            },
            "status": "running",
            "history": history,
        }

    def confirm_node(state: AgentState) -> dict[str, Any]:
        """HITL: interrupt when the tool requires confirmation."""
        history = list(state.get("history") or [])
        pending = state.get("pending_action") or {}
        tool_name = pending.get("tool", "")
        spec = registry.get(tool_name)

        needs = bool(spec and spec.requires_confirmation)
        if not needs:
            return {"status": "running", "history": history}

        prompt = (
            f"工具 `{tool_name}` 需要人工确认才能执行。\n"
            f"原因: {pending.get('reason', '')}\n"
            f"参数: {json.dumps(pending.get('args') or {}, ensure_ascii=False)}\n"
            f"请选择："
        )
        options = ["同意执行", "跳过", "取消任务"]
        history.append(f"[confirm] 请求 HITL: {options}")

        # Pause the graph; resume value comes back via Command(resume=...)
        choice = interrupt(
            {
                "prompt": prompt,
                "options": options,
                "tool": tool_name,
                "args": pending.get("args") or {},
            }
        )

        history.append(f"[confirm] 用户选择: {choice}")
        if choice == "取消任务":
            return {
                "status": "cancelled",
                "pending_action": None,
                "history": history,
            }
        if choice == "跳过":
            new_index = int(state.get("step_index") or 0) + 1
            plan = state.get("plan") or []
            new_status = "done" if new_index >= len(plan) else "running"
            if new_status == "done":
                history.append("[done] 计划全部完成（最后一步已跳过）")
            return {
                "status": new_status,
                "pending_action": None,  # skip execute; advance in after_tool
                "last_tool_result": f"(已跳过) {tool_name}",
                "step_index": new_index,
                "history": history,
            }
        # 同意执行
        return {"status": "running", "history": history}

    def execute_node(state: AgentState) -> dict[str, Any]:
        """Run the pending tool (or no-op if already skipped)."""
        history = list(state.get("history") or [])
        pending = state.get("pending_action")
        step_index = int(state.get("step_index") or 0)

        if not pending:
            # Skipped in confirm_node; step_index already advanced
            history.append("[execute] 无待执行动作（可能已跳过）")
            return {"history": history, "status": "running"}

        tool_name = pending.get("tool", "")
        args = dict(pending.get("args") or {})
        try:
            result = registry.call(tool_name, **args)
            result_s = str(result)
            history.append(f"[execute] {tool_name}({args}) → {result_s}")
            new_index = step_index + 1
            plan = state.get("plan") or []
            new_status = "done" if new_index >= len(plan) else "running"
            if new_status == "done":
                history.append("[done] 计划全部完成")
            return {
                "last_tool_result": result_s,
                "pending_action": None,
                "step_index": new_index,
                "status": new_status,
                "history": history,
            }
        except Exception as exc:  # noqa: BLE001
            history.append(f"[execute] 错误: {exc}")
            return {
                "last_tool_result": f"ERROR: {exc}",
                "pending_action": None,
                "status": "error",
                "history": history,
            }

    return reason_node, decide_node, confirm_node, execute_node


def _route_after_decide(state: AgentState) -> Literal["confirm", "__end__"]:
    if state.get("status") == "done" or not state.get("pending_action"):
        return "__end__"
    return "confirm"


def _route_after_confirm(state: AgentState) -> Literal["execute", "__end__"]:
    if state.get("status") == "cancelled":
        return "__end__"
    return "execute"


def _route_after_execute(state: AgentState) -> Literal["decide", "__end__"]:
    status = state.get("status")
    if status in ("cancelled", "error", "done"):
        return "__end__"
    plan = state.get("plan") or []
    step_index = int(state.get("step_index") or 0)
    if step_index >= len(plan):
        return "__end__"
    return "decide"


def build_graph(
    registry: ToolRegistry | None = None,
    demo: bool = True,
    checkpointer: MemorySaver | None = None,
):
    """Compile the agent StateGraph with HITL interrupt support."""
    registry = registry or get_default_registry()
    reason_node, decide_node, confirm_node, execute_node = make_nodes(
        registry, demo=demo
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
        {"decide": "decide", "__end__": END},
    )

    saver = checkpointer if checkpointer is not None else MemorySaver()
    return g.compile(checkpointer=saver)


__all__ = ["build_graph", "build_demo_plan", "Command"]
