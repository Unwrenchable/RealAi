"""Executive loop — act → sense → judge for unfinished goals."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from realai.executive.goal import Goal, append_goal_event, load_goals


JudgeFn = Callable[[Goal, Dict[str, Any]], str]  # returns verified|retry|failed|blocked_human
ActFn = Callable[[Goal], Dict[str, Any]]


class ExecutiveLoop:
    """Owns the goal graph. Specialists stay in Hive; this owns continuity."""

    def __init__(self, workspace: Optional[Path] = None):
        self.workspace = Path(workspace or r"C:\RealAI-clean")
        self.handlers: Dict[str, ActFn] = {}
        self.judges: Dict[str, JudgeFn] = {}

    def register(self, goal_type: str, act: ActFn, judge: JudgeFn) -> None:
        self.handlers[goal_type] = act
        self.judges[goal_type] = judge

    def open_goals(self) -> List[Goal]:
        return [g for g in load_goals(self.workspace) if g.status in {"open", "acting", "verifying", "failed"}]

    def tick(self, goal: Goal) -> Dict[str, Any]:
        act = self.handlers.get(goal.type)
        judge = self.judges.get(goal.type)
        if not act or not judge:
            append_goal_event(goal, {"kind": "error", "detail": f"no handler for {goal.type}"}, self.workspace)
            return {"ok": False, "error": "no handler"}

        goal.status = "acting"
        append_goal_event(goal, {"kind": "act_start"}, self.workspace)
        evidence = act(goal)
        goal.last_evidence = evidence
        goal.status = "verifying"
        append_goal_event(goal, {"kind": "evidence", "evidence": evidence}, self.workspace)

        verdict = judge(goal, evidence)
        goal.last_verdict = verdict
        if verdict == "verified":
            goal.status = "verified"
        elif verdict == "blocked_human":
            goal.status = "blocked_human"
        elif verdict == "retry":
            goal.status = "open"
            goal.retries += 1
        else:
            goal.status = "failed"
        append_goal_event(goal, {"kind": "verdict", "verdict": verdict}, self.workspace)
        return {"ok": True, "goal_id": goal.id, "status": goal.status, "verdict": verdict, "evidence": evidence}

    def run_once(self) -> List[Dict[str, Any]]:
        results = []
        for g in self.open_goals():
            results.append(self.tick(g))
        return results