"""Playtester loop: QA agents run harness cases; findings go to the owning agent on the MessageBus.

Case format (JSON, data/teams/<team>/playtests/*.json)::

  {"id": "radio-escape", "area": "frontend", "input": "...", "expected_contains": "..."}

A case may also carry a Python callable under "check" (tests / routines) returning (ok, detail).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from realai.agent_runtime.agent_runtime import MessageBus
from realai.agentx.providers.router import ProviderRouter

from .teams import Team

QA_AGENTS = ("game-qa-lead", "wastlandqa")


def load_cases(team: Team) -> list[dict[str, Any]]:
    d = team.path.parent / "playtests"
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(d.glob("*.json"))] if d.is_dir() else []


@dataclass
class PlaytestLoop:
    team: Team
    bus: MessageBus = field(default_factory=MessageBus)
    qa_agent: str = "game-qa-lead"
    dry_run: bool = True

    def _run_case(self, case: dict[str, Any]) -> tuple[bool, str]:
        check: Callable[[dict[str, Any]], tuple[bool, str]] | None = case.get("check")
        if callable(check):
            return check(case)
        out = ProviderRouter().select_provider(["qa"], ["local"]).complete(case.get("input", ""), {}, self.dry_run)
        content = str(out.get("content") or out.get("response") or "")
        exp = case.get("expected_contains")
        ok = exp is None or exp in content
        return ok, content[:300]

    def run(self, cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        cases = cases if cases is not None else load_cases(self.team)
        findings = []
        for case in cases:
            ok, detail = self._run_case(case)
            if ok:
                continue
            own = self.team.owner_for(case.get("area", "") + " " + case.get("input", ""))
            owner = own.owner if own else self.team.lead
            event = {
                "agent": self.qa_agent, "event": "qa.finding", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "task": case.get("id", "case"), "area": case.get("area", "game"), "status": "failed",
                "summary": f"Playtest case {case.get('id')} failed", "details": {"observed": detail, "owner": owner,
                                                                                 "reviewer": own.reviewer if own else None},
            }
            self.bus.send(self.qa_agent, owner, event, metadata={"type": "qa.finding", "team": self.team.id})
            if own and own.reviewer:
                self.bus.send(self.qa_agent, own.reviewer, event, metadata={"type": "qa.finding.cc", "team": self.team.id})
            findings.append(event)
        return {"team": self.team.id, "total": len(cases), "failed": len(findings), "findings": findings}
