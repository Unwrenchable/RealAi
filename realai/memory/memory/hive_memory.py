"""Hive memory ability — Json / SQLite / Redis / Chroma with safe fallbacks."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ABILITY = {
    "id": "hive_memory",
    "name": "hive_memory",
    "type": "ability",
    "status": "LIVE",
    "source": "agent_tools.engine.memory",
    "dest": "abilities/hive_memory.py",
    "capabilities": ["kv_memory", "vector_memory", "agent_state", "world_model_deltas"],
    "secrets_policy": "none — no wallet keys in memory payloads",
}


def _root() -> Path:
    return Path(os.environ.get("REALAI_HOME") or Path(__file__).resolve().parents[1])


def _adapter(kind: str):
    from agent_tools.engine.memory import (
        ChromaVectorMemoryAdapter,
        JsonFileMemoryAdapter,
        RedisMemoryAdapter,
        SQLiteMemoryAdapter,
        VectorMemoryAdapter,
    )

    root = _root()
    mem_dir = root / "memory" / "hive"
    mem_dir.mkdir(parents=True, exist_ok=True)
    kind = (kind or "sqlite").lower()
    if kind in {"json", "file"}:
        return "json", JsonFileMemoryAdapter(mem_dir / "memory.json")
    if kind in {"redis"}:
        try:
            # Prefer soft redis; fall back if runtime not configured
            ad = RedisMemoryAdapter()
            # probe
            ad.read("__probe__", limit=1)
            return "redis", ad
        except Exception:
            return "sqlite_fallback", SQLiteMemoryAdapter(mem_dir / "memory.sqlite3")
    if kind in {"chroma", "vector_chroma"}:
        try:
            return "chroma", ChromaVectorMemoryAdapter(mem_dir)
        except Exception:
            return "vector_fallback", VectorMemoryAdapter()
    if kind in {"vector", "memory"}:
        return "vector", VectorMemoryAdapter()
    return "sqlite", SQLiteMemoryAdapter(mem_dir / "memory.sqlite3")


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or "read").lower()
    namespace = str(ctx.get("namespace") or "default")
    kind = str(ctx.get("backend") or ctx.get("kind") or "sqlite")
    backend, ad = _adapter(kind)

    if action in {"append", "write", "store"}:
        value = ctx.get("value")
        if not isinstance(value, dict):
            value = {"text": input or str(ctx.get("text") or ""), "meta": ctx.get("meta") or {}}
        ad.append(namespace, value)
        return {"ok": True, "ability": "hive_memory", "action": "append", "backend": backend, "namespace": namespace}

    if action in {"search"}:
        query = str(ctx.get("query") or input or "")
        hits = ad.search(namespace, query, k=int(ctx.get("k") or 5))
        return {"ok": True, "ability": "hive_memory", "action": "search", "backend": backend, "hits": hits}

    if action in {"world_delta", "world_model_delta"}:
        # persist world-model delta under dedicated namespace
        delta = ctx.get("delta") if isinstance(ctx.get("delta"), dict) else {"text": input, "delta": ctx.get("delta")}
        ad.append("world_model_deltas", delta)
        return {"ok": True, "ability": "hive_memory", "action": "world_delta", "backend": backend}

    # default read
    rows = ad.read(namespace, limit=int(ctx.get("limit") or 20))
    return {
        "ok": True,
        "ability": "hive_memory",
        "action": "read",
        "backend": backend,
        "namespace": namespace,
        "rows": rows,
    }
