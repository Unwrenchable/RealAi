"""Memory & persistent learning — Aura + hive memory adapters."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "memory_learning",
    "name": "memory_learning",
    "type": "ability",
    "status": "LIVE",
    "source": "realai.aura_memory + abilities.hive_memory",
    "dest": "abilities/memory_learning.py",
    "capabilities": ["remember", "recall", "hive_kv", "vector_memory"],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or "recall").lower()
    backend = str(ctx.get("backend") or "aura").lower()

    if backend in {"hive", "sqlite", "chroma", "redis", "json"}:
        from abilities.hive_memory import run as hive_run

        return {
            **hive_run(input=input, context={**ctx, "backend": backend if backend != "hive" else "sqlite"}),
            "ability": "memory_learning",
            "layer": "hive_memory",
        }

    from realai.aura_memory import AuraMemory

    mem = AuraMemory()
    if action in {"remember", "write", "store", "append"}:
        text = str(ctx.get("text") or input or "").strip()
        if not text:
            return {"ok": False, "error": "text_required", "ability": "memory_learning"}
        mem.remember(text, metadata=ctx.get("metadata") if isinstance(ctx.get("metadata"), dict) else None)
        return {"ok": True, "ability": "memory_learning", "action": "remember", "layer": "aura"}
    query = str(ctx.get("query") or input or "")
    hits = mem.recall(query, top_k=int(ctx.get("top_k") or 5))
    return {
        "ok": True,
        "ability": "memory_learning",
        "action": "recall",
        "layer": "aura",
        "query": query,
        "memories": hits,
        "count": len(hits) if isinstance(hits, list) else 0,
        "chat_inject": "REALAI_MEMORY_INJECT / aura_memory tool",
    }
