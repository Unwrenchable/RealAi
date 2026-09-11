"""Repo Health Watcher — first executive slice.

Goal: realai package stays importable / bootable surface intact.
Evidence: file presence + optional keyword checks (static-friendly).
Human gate: force-push, delete.

This module defines the goal and evidence rules. It does not start a daemon
and does not run heal during reconstruction.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from realai.executive.evidence import file_exists
from realai.executive.goal import Goal, append_goal_event, goals_path
from realai.executive.loop import ExecutiveLoop

GOAL_TYPE = "repo_health"
GOAL_TITLE = "realai.main stays bootable; dispatcher/hive surfaces present"


def required_paths(workspace: Path) -> List[Path]:
    return [
        workspace / "realai" / "__main__.py",
        workspace / "realai" / "v3_runtime_bridge.py",
        workspace / "realai" / "v3_orchestrator.py",
        workspace / "realai" / "cli" / "craft.py",
        workspace / "realai" / "cli" / "hive" / "app.py",
        workspace / ".github" / "agents" / "overseer.json",
        workspace / "realai" / "universe" / "mode.py",
        workspace / "realai" / "executive" / "loop.py",
    ]


def act(goal: Goal) -> Dict[str, Any]:
    ws = Path(goal.meta.get("workspace") or os.environ.get("REALAI_WORKSPACE") or r"C:\RealAI-clean")
    checks = []
    missing = []
    for p in required_paths(ws):
        row = file_exists(p)
        checks.append(row)
        if not row["ok"]:
            missing.append(str(p))
    return {
        "ok": len(missing) == 0,
        "workspace": str(ws),
        "checks": checks,
        "missing": missing,
        "note": "File-surface bootability. Does not import-execute RealAI.",
    }


def judge(goal: Goal, evidence: Dict[str, Any]) -> str:
    if evidence.get("ok"):
        return "verified"
    # Missing shims are retryable reconstruction targets, not human gates
    if evidence.get("missing"):
        return "retry" if goal.retries < 3 else "failed"
    return "failed"


def seed_goal(workspace: Path | None = None) -> Goal:
    ws = Path(workspace or r"C:\RealAI-clean")
    g = Goal.new(GOAL_TYPE, GOAL_TITLE, workspace=str(ws))
    append_goal_event(g, {"kind": "seed", "slice": "repo_health"}, ws)
    return g


def attach(loop: ExecutiveLoop) -> None:
    loop.register(GOAL_TYPE, act, judge)


def spoken_status(workspace: Path | None = None) -> str:
    """One-line status for Voice Lab: what did you do last night?"""
    from realai.executive.goal import load_goals

    ws = Path(workspace or r"C:\RealAI-clean")
    goals = [g for g in load_goals(ws) if g.type == GOAL_TYPE]
    if not goals:
        return "No repo health goals on the books yet."
    g = sorted(goals, key=lambda x: x.updated_at, reverse=True)[0]
    miss = (g.last_evidence or {}).get("missing") or []
    if g.status == "verified":
        return f"Repo health verified. Goal {g.id[:8]} is green."
    if miss:
        return f"Repo health still open. Missing {len(miss)} paths. Last verdict {g.last_verdict or 'none'}."
    return f"Repo health status {g.status}. Verdict {g.last_verdict or 'none'}."