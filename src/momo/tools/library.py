"""In-memory tiny library store + search/get tools (prototype)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from momo.tools.registry import ToolRegistry

# 原型用内存文档库（后续可换真实向量库 / Notion 等）
LIBRARY_DOCS: dict[str, dict[str, str]] = {
    "momo-kernel": {
        "title": "Momo Agent 底座",
        "body": (
            "Momo 内核：reason → decide → confirm(HITL) → execute。"
            " 工具失败可重试，超限则 status=blocked。"
            " 场景能力通过 plugins 挂载，不进内核。"
        ),
    },
    "momo-hitl": {
        "title": "人工确认 HITL",
        "body": (
            "敏感工具标记 requires_confirmation=True 时，"
            "confirm 节点使用 LangGraph interrupt 暂停，"
            "CLI 通过 Command(resume=...) 恢复。"
        ),
    },
    "momo-provider": {
        "title": "模型 Provider",
        "body": (
            "MOMO_PROVIDER=demo|openai|ollama。"
            " DemoProvider 离线确定性；openai/ollama 可选，"
            "失败时 reason 节点回退到 build_demo_plan。"
        ),
    },
}


def search_library(query: str = "") -> str:
    """Keyword search over the in-memory library. Returns matching doc ids/snippets."""
    q = (query or "").strip().lower()
    if not q:
        ids = ", ".join(LIBRARY_DOCS.keys())
        return f"库中共 {len(LIBRARY_DOCS)} 篇文档。请提供关键词。文档 id: {ids}"

    hits: list[str] = []
    for doc_id, doc in LIBRARY_DOCS.items():
        blob = f"{doc_id} {doc.get('title', '')} {doc.get('body', '')}".lower()
        if q in blob or any(tok in blob for tok in q.split() if tok):
            title = doc.get("title", doc_id)
            snippet = (doc.get("body") or "")[:80]
            hits.append(f"- {doc_id}: {title} — {snippet}...")

    if not hits:
        return f"未找到与「{query}」相关的文档。"
    return f"搜索「{query}」命中 {len(hits)} 条:\n" + "\n".join(hits)


def get_library_context(doc_id: str = "") -> str:
    """Fetch one document by id from the in-memory library."""
    key = (doc_id or "").strip()
    if not key:
        return "请提供 doc_id。"
    doc = LIBRARY_DOCS.get(key)
    if doc is None:
        known = ", ".join(LIBRARY_DOCS.keys())
        return f"未知 doc_id={key!r}。可用: {known}"
    return f"[{key}] {doc.get('title', '')}\n{doc.get('body', '')}"


def register_library_tools(registry: "ToolRegistry") -> None:
    registry.register(
        "search_library",
        search_library,
        description="在内存文档库中按关键词搜索。参数: query (str)",
        requires_confirmation=False,
    )
    registry.register(
        "get_library_context",
        get_library_context,
        description="按 doc_id 取回一篇文档全文。参数: doc_id (str)",
        requires_confirmation=False,
    )
