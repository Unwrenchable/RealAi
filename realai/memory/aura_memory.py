"""
Aura memory facade — recovered gold for the missing `aura_memory.py` name.

Sources (best → fallback):
  1. aura.memory.engine  (realai2 — JSON long-term store + get_memory())
  2. aura.memory         (package init)
  3. aura.memory module file (simple text store)

The basename aura_memory.py never existed under Users\\tsmit; this is the
canonical import path for that capability.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

LongTermMemory = None  # type: ignore
WorkingMemory = None  # type: ignore
get_memory = None  # type: ignore

# Prefer richer engine
try:
    from aura.memory.engine import (  # type: ignore
        LongTermMemory,
        WorkingMemory,
        get_memory,
    )
except Exception:
    try:
        from aura.memory import LongTermMemory, WorkingMemory  # type: ignore
    except Exception:
        # Inline minimal fallback
        import json
        from datetime import datetime

        class LongTermMemory:  # type: ignore
            def __init__(self, memory_path: str = "aura/memory_store"):
                self.memory_path = Path(memory_path)
                self.memory_path.mkdir(parents=True, exist_ok=True)

            def remember(self, experience: str, metadata: Optional[Dict] = None):
                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                entry = {"timestamp": ts, "experience": experience, "metadata": metadata or {}}
                (self.memory_path / f"exp_{ts}.json").write_text(
                    json.dumps(entry, indent=2), encoding="utf-8"
                )

            def recall(self, query: str = "", top_k: int = 10) -> List[Any]:
                files = sorted(
                    self.memory_path.glob("exp_*.json"),
                    key=lambda f: f.stat().st_mtime,
                    reverse=True,
                )
                out = []
                for f in files[:top_k]:
                    try:
                        out.append(json.loads(f.read_text(encoding="utf-8")))
                    except Exception:
                        continue
                return out

        class WorkingMemory:  # type: ignore
            def __init__(self, max_results: int = 20):
                self.current_plan = None
                self.recent_results: List[Any] = []
                self.max_results = max_results
                self.context: Dict[str, Any] = {}

            def update_plan(self, plan):
                self.current_plan = plan

            def add_result(self, result):
                self.recent_results.append(result)
                if len(self.recent_results) > self.max_results:
                    self.recent_results.pop(0)


class AuraMemory:
    """Unified adapter expected by callers of aura_memory."""

    def __init__(self, memory_path: Optional[str] = None):
        path = memory_path or str(_ROOT / "aura" / "memory_store")
        try:
            self.long_term = LongTermMemory(path)  # type: ignore
        except TypeError:
            self.long_term = LongTermMemory()  # type: ignore
        self.working = WorkingMemory()  # type: ignore

    def remember(self, experience: str, metadata: Optional[Dict] = None) -> None:
        try:
            self.long_term.remember(experience, metadata=metadata)  # type: ignore
        except TypeError:
            self.long_term.remember(experience)  # type: ignore

    def recall(self, query: str = "", top_k: int = 5) -> list:
        try:
            return self.long_term.recall(query, top_k=top_k)  # type: ignore
        except TypeError:
            return self.long_term.recall(query, top_k)  # type: ignore

    def update_plan(self, plan: Any) -> None:
        self.working.update_plan(plan)

    def add_result(self, result: Any) -> None:
        self.working.add_result(result)


__all__ = ["AuraMemory", "LongTermMemory", "WorkingMemory", "get_memory"]
