"""CLI entry: demo mode (no API key) with HITL pause/resume."""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from typing import Any

from langgraph.types import Command

from momo.graph import build_graph
from momo.provider import get_provider


OPTIONS = ("同意执行", "跳过", "取消任务")


def _print_banner() -> None:
    print("=" * 56)
    print("  Momo  ·  Agent 底座 / HITL 原型")
    print("=" * 56)


def _print_interrupt(payload: Any) -> None:
    if isinstance(payload, dict):
        prompt = payload.get("prompt") or "需要确认"
        options = payload.get("options") or list(OPTIONS)
        print()
        print("-" * 56)
        print("[HITL] 图已暂停，等待你的选择：")
        print(prompt)
        for i, opt in enumerate(options, 1):
            print(f"  {i}. {opt}")
        print("-" * 56)
    else:
        print(f"[HITL] {payload}")


def _read_choice(options: list[str] | tuple[str, ...] = OPTIONS) -> str:
    options = list(options)
    while True:
        raw = input("请输入选项编号或全文 > ").strip()
        if not raw:
            continue
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        if raw in options:
            return raw
        aliases = {
            "y": "同意执行",
            "yes": "同意执行",
            "approve": "同意执行",
            "ok": "同意执行",
            "s": "跳过",
            "skip": "跳过",
            "c": "取消任务",
            "cancel": "取消任务",
            "n": "取消任务",
        }
        if raw.lower() in aliases:
            return aliases[raw.lower()]
        print(f"无效输入，请从中选择: {options}")


def _collect_interrupts(snap: Any) -> list[Any]:
    """LangGraph 0.3: interrupts live on snap.tasks[*].interrupts."""
    payloads: list[Any] = []
    direct = getattr(snap, "interrupts", None) or ()
    for item in direct:
        payloads.append(getattr(item, "value", item))
    for task in getattr(snap, "tasks", None) or ():
        for item in getattr(task, "interrupts", None) or ():
            payloads.append(getattr(item, "value", item))
    return payloads


def run_agent(
    task: str,
    *,
    demo: bool = True,
    thread_id: str | None = None,
    auto_choice: str | None = None,
    max_tool_retries: int = 1,
) -> dict[str, Any]:
    """Run until completion, handling interrupts interactively (or auto_choice)."""
    provider_name = "demo" if demo else (os.environ.get("MOMO_PROVIDER") or "demo")
    provider = get_provider(provider_name)
    graph = build_graph(
        demo=demo,
        provider=provider,
        max_tool_retries=max_tool_retries,
    )
    tid = thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": tid}}

    _print_banner()
    print(f"thread_id = {tid}")
    print(f"task      = {task}")
    print(f"mode      = {'demo (无 LLM)' if demo else 'llm/fallback'}")
    print(f"provider  = {provider.name}")
    print(f"retries   = {max_tool_retries}")
    print()

    values: dict[str, Any] = graph.invoke(
        {
            "task": task,
            "messages": [],
            "plan": [],
            "step_index": 0,
            "pending_action": None,
            "last_tool_result": None,
            "status": "running",
            "history": [],
            "tool_retries": 0,
            "block_reason": None,
            "max_tool_retries": max_tool_retries,
        },
        config=config,
    )

    while True:
        snap = graph.get_state(config)
        payloads = _collect_interrupts(snap)
        if not payloads:
            values = snap.values if getattr(snap, "values", None) is not None else values
            break

        payload = payloads[0]
        _print_interrupt(payload)
        opts = list(OPTIONS)
        if isinstance(payload, dict) and payload.get("options"):
            opts = list(payload["options"])

        if auto_choice:
            choice = auto_choice if auto_choice in opts else opts[0]
            print(f"(auto) 选择 → {choice}")
        else:
            choice = _read_choice(opts)

        values = graph.invoke(Command(resume=choice), config=config)

        if choice == "取消任务":
            snap = graph.get_state(config)
            values = snap.values if getattr(snap, "values", None) is not None else values
            break

    _print_summary(values)
    return values


def _print_summary(values: dict[str, Any] | None) -> None:
    values = values or {}
    print()
    print("=" * 56)
    print("  运行结束")
    print("=" * 56)
    print(f"status           = {values.get('status')}")
    print(f"step_index       = {values.get('step_index')}")
    print(f"last_tool_result = {values.get('last_tool_result')}")
    if values.get("block_reason"):
        print(f"block_reason     = {values.get('block_reason')}")
    hist = values.get("history") or []
    if hist:
        print("history:")
        for line in hist:
            print(f"  {line}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Momo：Agent 底座（工具 + HITL + 重试/阻塞 + Provider）"
    )
    parser.add_argument(
        "task",
        nargs="*",
        default=[],
        help="任务描述（默认使用演示任务）",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        default=True,
        help="离线演示模式（默认开启，无需 API Key）",
    )
    parser.add_argument(
        "--no-demo",
        action="store_true",
        help="关闭演示标记（仍会在无 LLM 时回退到演示规划）",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="HITL 自动选择「同意执行」（便于非交互验证）",
    )
    parser.add_argument(
        "--auto-skip",
        action="store_true",
        help="HITL 自动选择「跳过」",
    )
    parser.add_argument(
        "--auto-cancel",
        action="store_true",
        help="HITL 自动选择「取消任务」",
    )
    parser.add_argument(
        "--max-tool-retries",
        type=int,
        default=1,
        help="工具失败后额外重试次数（默认 1）",
    )
    args = parser.parse_args(argv)

    demo = not args.no_demo
    task = " ".join(args.task).strip() or "演示：库检索、HITL 确认与失败重试"

    auto_choice = None
    if args.auto_approve:
        auto_choice = "同意执行"
    elif args.auto_skip:
        auto_choice = "跳过"
    elif args.auto_cancel:
        auto_choice = "取消任务"

    try:
        values = run_agent(
            task,
            demo=demo,
            auto_choice=auto_choice,
            max_tool_retries=max(0, int(args.max_tool_retries)),
        )
    except KeyboardInterrupt:
        print("\n已中断。", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"运行失败: {exc}", file=sys.stderr)
        raise

    status = (values or {}).get("status")
    if status == "cancelled":
        return 2
    if status in ("error", "blocked"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
