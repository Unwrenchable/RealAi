"""SQLite-backed memory store with embedding search."""

import json
import math
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

from core.logging.logger import log
from core.memory.base import MemoryStore


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    size = min(len(a), len(b))
    ax = a[:size]
    bx = b[:size]
    dot = sum(x * y for x, y in zip(ax, bx))
    an = math.sqrt(sum(x * x for x in ax)) or 1.0
    bn = math.sqrt(sum(x * x for x in bx)) or 1.0
    return dot / (an * bn)


class SQLiteMemoryStore(MemoryStore):
    """Simple sqlite memory implementation with linear vector search."""

    def __init__(self, path: str = "realai_memory.sqlite3"):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS memory ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "user_id TEXT NOT NULL, "
            "type TEXT NOT NULL, "
            "content TEXT NOT NULL, "
            "embedding TEXT NOT NULL, "
            "timestamp INTEGER NOT NULL)"
        )
        self._conn.commit()

    def add(self, user_id: str, items: List[Dict[str, Any]]) -> None:
        if not items:
            return
        log("memory.write", {"user_id": user_id, "items": len(items)})
        with self._lock:
            for item in items:
                content = str(item.get("content", ""))
                embedding = item.get("embedding", []) or []
                item_type = str(item.get("type", "message"))
                ts = int(item.get("timestamp", int(time.time())))
                self._conn.execute(
                    "INSERT INTO memory(user_id, type, content, embedding, timestamp) VALUES(?, ?, ?, ?, ?)",
                    (user_id, item_type, content, json.dumps(embedding), ts),
                )
            self._conn.commit()

    def search(self, user_id: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
        query_embedding = _embedding_from_text(query)
        rows = self._conn.execute(
            "SELECT type, content, embedding, timestamp FROM memory WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        ranked: List[Dict[str, Any]] = []
        for row in rows:
            item_type, content, embedding_json, ts = row
            emb = json.loads(embedding_json) if embedding_json else []
            score = _cosine(query_embedding, emb)
            ranked.append({
                "type": item_type,
                "content": content,
                "embedding": emb,
                "timestamp": ts,
                "score": score,
            })
        ranked.sort(key=lambda item: item["score"], reverse=True)
        results = ranked[: max(0, int(k))]
        log("memory.read", {"user_id": user_id, "query": query, "results": len(results)})
        return results

    def clear(self, user_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM memory WHERE user_id = ?", (user_id,))
            self._conn.commit()


def _embedding_from_text(text: str) -> List[float]:
    # Deterministic fallback embedding for local memory when no real embedder is injected.
    digest = [float((ord(char) % 32) / 31.0) for char in (text or "")[:32]]
    if not digest:
        digest = [0.0]
    while len(digest) < 10:
        digest.append(0.0)
    return digest[:10]
