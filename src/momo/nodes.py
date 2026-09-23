"""Graph node factories: reason / decide / confirm / execute."""

from __future__ import annotations

import json
from typing import Any

from langgraph.types import interrupt

from momo.demo_plan import build_demo_plan, try_provider_plan
from momo.provider import ModelProvider, get_provider
from momo.state import AgentState
from momo.tools.builtin import reset_flaky_counters
from momo.tools.registry import ToolRegistry


def make_nodes(
    registry: ToolRegistry,
    demo: bool = True,
    provider: ModelProvider | None = None,
    max_tool_retries: int = 1,
):
    provider = provider or get_provider("demo" if demo else None)

    def reason_node(state: AgentState) -> dict[str, Any]:
        """Think / plan next steps."""
        history = list(state.get("history") or [])
        plan = list(state.get("plan") or [])
        step_index = int(state.get("step_index") or 0)
        retries_cap = int(
            state.get("max_tool_retries")
            if state.get("max_tool_retries") is not None
            else max_tool_retries
        )

        if not plan:
            task = state.get("task") or ""
            if demo:
                # 演示模式：重置 flaky 计数，保证可重复
                reset_flaky_counters()
                plan = build_demo_plan(task)
                history.append(f"[reason] 使用离线演示规划器，共 {len(plan)} 步")
            else:
                llm_plan = try_provider_plan(provider, task, history)
                if llm_plan:
                    plan = llm_plan
                else:
                    reset_flaky_counters()
                    plan = build_demo_plan(task)
                    history.append(
                        f"[reason] 回退到演示规划器，共 {len(plan)} 步"
                    )

        return {
            "plan": plan,
            "step_index": step_index,
            "status": "running",
            "history": history,
            "tool_retries": 0,
            "block_reason": None,
            "max_tool_retries": retries_cap,
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
        spec = registry.get(tool_name)
        needs_confirm = bool(spec and spec.requires_confirmation)
        return {
            "pending_action": {
                "tool": tool_name,
                "args": args,
                "reason": reason,
            },
            "status": "awaiting_confirm" if needs_confirm else "running",
            "history": history,
            "tool_retries": 0,  # 新步骤清零重试
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
                "pending_action": None,
                "last_tool_result": f"(已跳过) {tool_name}",
                "step_index": new_index,
                "history": history,
                "tool_retries": 0,
            }
        # 同意执行
        return {"status": "running", "history": history}

    def execute_node(state: AgentState) -> dict[str, Any]:
        """Run the pending tool; on failure retry then set status=blocked."""
        history = list(state.get("history") or [])
        pending = state.get("pending_action")
        step_index = int(state.get("step_index") or 0)
        retries_used = int(state.get("tool_retries") or 0)
        max_retries = int(
            state.get("max_tool_retries")
            if state.get("max_tool_retries") is not None
            else max_tool_retries
        )

        if not pending:
            history.append("[execute] 无待执行动作（可能已跳过）")
            return {"history": history, "status": "running"}

        tool_name = pending.get("tool", "")
        args = dict(pending.get("args") or {})

        try:
            result = registry.call(tool_name, **args)
            result_s = str(result)
            if retries_used > 0:
                history.append(
                    f"[execute] {tool_name}({args}) → {result_s} "
                    f"(重试成功，此前失败 {retries_used} 次)"
                )
            else:
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
                "tool_retries": 0,
                "block_reason": None,
            }
        except Exception as exc:  # noqa: BLE001
            err_s = str(exc)
            if retries_used < max_retries:
                history.append(
                    f"[execute] 错误(将重试 {retries_used + 1}/{max_retries}): {err_s}"
                )
                # 保留 pending_action，增加重试计数；路由回 execute
                return {
                    "last_tool_result": f"ERROR(retry): {err_s}",
                    "status": "running",
                    "history": history,
                    "tool_retries": retries_used + 1,
                    "block_reason": None,
                }
            # 重试耗尽 → blocked（明确原因，非 silent generic error）
            block_reason = (
                f"工具 `{tool_name}` 失败且已重试 {retries_used} 次"
                f"（上限 {max_retries}）: {err_s}"
            )
            history.append(f"[blocked] {block_reason}")
            return {
                "last_tool_result": f"BLOCKED: {err_s}",
                "pending_action": None,
                "status": "blocked",
                "block_reason": block_reason,
                "history": history,
                "tool_retries": retries_used,
            }

    return reason_node, decide_node, confirm_node, execute_node
