"""RackUp health watcher scaffold - file/env markers only, no network.

Goal type: rackup_health
Detects RackUp-related surface files and optional REALAI_RACKUP_MARK env.
Does not start coaches, adapters, or any network client.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from realai.executive.goal import Goal, append_goal_event
from realai.executive.loop import ExecutiveLoop

GOAL_TYPE = "rackup_health"
GOAL_TITLE = "RackUp surface markers present (scaffold)"
ENV_MARK = "REALAI_RACKUP_MARK"


def marker_paths(workspace: Path) -> List[Path]:
    return [
        workspace / "realai" / "adapters" / "rackup_coach.py",
        workspace / "realai" / "abilities" / "rackup",
        workspace / "realai" / "plugins" / "rackup_coach",
        workspace / "realai" / "plugins" / "rackup-coach",
    ]


def _path_ok(path: Path) -> Dict[str, Any]:
    exists = path.exists()
    kind = "missing"
    size = 0
    if path.is_file():
        kind = "file"
        size = path.stat().st_size
    elif path.is_dir():
        kind = "dir"
        size = sum(1 for _ in path.iterdir()) if exists else 0
    return {"ok": exists, "path": str(path), "kind": kind, "size": size}


def act(goal: Goal) -> Dict[str, Any]:
    ws = Path(goal.meta.get("workspace") or os.environ.get("REALAI_WORKSPACE") or r"C:\RealAI-clean")
    checks = [_path_ok(p) for p in marker_paths(ws)]
    missing = [c["path"] for c in checks if not c["ok"]]
    env_mark = os.environ.get(ENV_MARK)
    env_ok = bool(env_mark)
    # Scaffold: verified if at least one marker path exists OR env mark is set
    any_path = any(c["ok"] for c in checks)
    return {
        "ok": any_path or env_ok,
        "workspace": str(ws),
        "checks": checks,
        "missing": missing,
        "env_mark": ENV_MARK,
        "env_present": env_ok,
        "note": "Scaffold only. File/env markers; no network.",
    }


def judge(goal: Goal, evidence: Dict[str, Any]) -> str:
    if evidence.get("ok"):
        return "verified"
    if goal.retries < 3:
        return "retry"
    return "failed"


def seed_goal(workspace: Path | None = None) -> Goal:
    ws = Path(workspace or r"C:\RealAI-clean")
    g = Goal.new(GOAL_TYPE, GOAL_TITLE, workspace=str(ws), slice="rackup_health")
    append_goal_event(g, {"kind": "seed", "slice": "rackup_health"}, ws)
    return g


def attach(loop: ExecutiveLoop) -> None:
    loop.register(GOAL_TYPE, act, judge)