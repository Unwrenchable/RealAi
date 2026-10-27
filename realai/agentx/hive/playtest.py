"""Playtester loop: QA agents run harness cases; findings go to the owning agent on the MessageBus.

Case format (JSON, data/teams/<team>/playtests/*.json)::

  {"id": "radio-escape", "area": "frontend", "input": "...", "expected_contains": "..."}

A case may also carry a Python callable under "check" (tests / routines) returning (ok, detail).
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from realai.agent_runtime.agent_runtime import MessageBus
from realai.agentx.providers.router import ProviderRouter

from .hive_client import pick_provider
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
    use_hive: bool | None = None
    findings_log: Path | None = None  # default: findings_path()
    last_run: dict[str, Any] | None = None
    run_id: str = ""

    def _run_case(self, case: dict[str, Any]) -> tuple[bool, str]:
        check: Callable[[dict[str, Any]], tuple[bool, str]] | None = case.get("check")
        if callable(check):
            return check(case)
        prov, fallback = pick_provider(["qa"], self.use_hive)
        root = self.team.workspace_root()
        if not fallback and root and hasattr(prov, "chat") and case.get("tools", True):
            from .agent_loop import run_agent
            from .fs_tools import SafeFS

            from functools import partial
            from . import events

            res = run_agent(prov.chat, SafeFS(root), case.get("input", ""), role=f"{self.qa_agent} playtester",
                            emit=partial(events.emit, run=self.run_id, team=self.team.id), agent=self.qa_agent,
                            max_steps=int(os.environ.get("REALAI_AGENT_MAX_STEPS", "8")))
            self.last_run = res
            if getattr(prov, "last_error", None) and not res["answer"].strip():
                return False, f"provider error: {prov.last_error}"
            out = {"content": res["answer"]}
            if res["cited_invented"]:
                return False, "invented paths: " + ", ".join(res["cited_invented"][:5]) + " | " + res["answer"][:200]
        else:
            out = prov.complete(case.get("input", ""), {"role": "playtester"}, self.dry_run if fallback else False)
        content = str(out.get("content") or out.get("response") or "")
        if out.get("error"):
            return False, f"provider error: {out['error']}"
        exp = case.get("expected_contains")
        ok = exp is None or exp in content
        if case.get("expect_nonempty"):
            ok = ok and bool(content.strip())
        return ok, content[:300]

    def run(self, cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        cases = cases if cases is not None else load_cases(self.team)
        from . import events

        self.run_id = self.run_id or f"pt-{int(time.time() * 1000)}"
        events.emit("run.started", run=self.run_id, team=self.team.id, kind="playtest", cases=len(cases))
        findings = []
        for case in cases:
            events.emit("step.started", run=self.run_id, team=self.team.id, agent=self.qa_agent, step=str(case.get("id")))
            ok, detail = self._run_case(case)
            events.emit("step.finished", run=self.run_id, team=self.team.id, agent=self.qa_agent, step=str(case.get("id")),
                        ok=ok, output=detail[:600], files_read=(self.last_run or {}).get("files_read", []))
            if ok:
                continue
            own = self.team.owner_for(case.get("area", "") + " " + case.get("input", ""))
            owner = own.owner if own else self.team.lead
            event = {
                "agent": self.qa_agent, "event": "qa.finding", "team": self.team.id, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "task": case.get("id", "case"), "area": case.get("area", "game"), "status": "failed",
                "summary": f"Playtest case {case.get('id')} failed", "details": {"observed": detail, "owner": owner,
                                                                                 "reviewer": own.reviewer if own else None},
            }
            self.bus.send(self.qa_agent, owner, event, metadata={"type": "qa.finding", "team": self.team.id})
            if own and own.reviewer:
                self.bus.send(self.qa_agent, own.reviewer, event, metadata={"type": "qa.finding.cc", "team": self.team.id})
            findings.append(event)
            events.emit("qa.finding", run=self.run_id, team=self.team.id, agent=self.qa_agent, owner=owner,
                        reviewer=own.reviewer if own else None, task=event["task"], summary=event["summary"],
                        observed=str(detail)[:400])
        record_findings(findings, self.findings_log)
        events.emit("run.finished", run=self.run_id, team=self.team.id, kind="playtest", failed=len(findings), total=len(cases))
        return {"team": self.team.id, "total": len(cases), "failed": len(findings), "findings": findings}


def findings_path() -> Path:
    root = Path(os.environ.get("REALAI_HOME") or Path(__file__).resolve().parents[3])
    return root / "memory" / "hive" / "findings.jsonl"


def record_findings(findings: list[dict[str, Any]], path: Path | None = None) -> None:
    if not findings:
        return
    p = path or findings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        for f in findings:
            fh.write(json.dumps(f, default=str) + "\n")


def read_findings(limit: int = 100, team: str | None = None, path: Path | None = None) -> list[dict[str, Any]]:
    p = path or findings_path()
    if not p.is_file():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if team and row.get("team") != team:
            continue
        rows.append(row)
    return rows[-max(1, limit):]
