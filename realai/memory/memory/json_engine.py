"""JSON file memory engine (legacy ``from core.memory import MemoryEngine``)."""

from __future__ import annotations

import json
import time
from pathlib import Path


class MemoryEngine:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.store = self._load()

    def _load(self):
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def store_value(self, key, value):
        self.store.setdefault(key, []).append({"ts": time.time(), "value": value})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.store, indent=2), encoding="utf-8")

    def fetch_recent(self, key, limit=5):
        return [e["value"] for e in self.store.get(key, [])[-limit:]]
