"""Goal objects with status, deadlines, last-evidence, owner."""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def goals_path(workspace: Optional[Path] = None) -> Path:
    root = Path(workspace or os.environ.get("REALAI_WORKSPACE") or r"C:\RealAI-clean")
    d = root / "realai" / "executive" / "state"
    d.mkdir(parents=True, exist_ok=True)
    return d / "goals.jsonl"


@dataclass
class Goal:
    id: str
    type: str
    title: str
    status: str = "open"  # open | acting | verifying | verified | failed | blocked_human
    owner: str = "executive"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    deadline: Optional[float] = None
    last_evidence: Optional[Dict[str, Any]] = None
    last_verdict: Optional[str] = None
    retries: int = 0
    human_gate: List[str] = field(default_factory=lambda: ["force-push", "delete", "spend", "chain-write"])
    meta: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def new(type_: str, title: str, **meta: Any) -> "Goal":
        return Goal(id=str(uuid.uuid4()), type=type_, title=title, meta=dict(meta))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Goal":
        return Goal(**{k: v for k, v in d.items() if k in Goal.__dataclass_fields__})


def append_goal_event(goal: Goal, event: Dict[str, Any], workspace: Optional[Path] = None) -> Path:
    path = goals_path(workspace)
    goal.updated_at = time.time()
    row = {"ts": time.time(), "goal": goal.to_dict(), "event": event}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def load_goals(workspace: Optional[Path] = None) -> List[Goal]:
    path = goals_path(workspace)
    if not path.is_file():
        return []
    latest: Dict[str, Goal] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            g = Goal.from_dict(row.get("goal") or row)
            latest[g.id] = g
        except Exception:
            continue
    return list(latest.values())