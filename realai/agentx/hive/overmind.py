"""Overmind: hive lead. plan -> route -> execute (local provider) -> summarize -> hive memory."""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from realai.agentx.engine.router import AgentRouter
from realai.agentx.providers.router import ProviderRouter

from .governance import CapabilityGuardian
from .hive_client import HiveProvider, pick_provider
from .registry import HiveRegistry, load_registry
from .teams import Team, load_teams


def plan(goal: str, max_steps: int = 8) -> list[str]:
    """task_planner (deterministic): split a goal into ordered steps."""
    parts = re.split(r"(?:\n+|;|\bthen\b|(?<=[.!?])\s+)", goal, flags=re.I)
    steps = [p.strip(" -*\t.") for p in parts if p and p.strip(" -*\t.")]
    return steps[:max_steps] or [goal.strip()]


def summarize(results: list[dict[str, Any]], limit: int = 600) -> str:
    """memory_summarizer (deterministic): compact record of what each agent did."""
    lines = [f"[{r['agent']}] {r['step'][:80]} -> {str(r.get('output', ''))[:120]}" for r in results]
    text = "\n".join(lines)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def remember(namespace: str, summary: str, meta: dict[str, Any]) -> dict[str, Any]:
    """Feed hive_memory (abilities.hive_memory, json backend); fall back to the engine adapter."""
    try:
        from abilities import hive_memory  # type: ignore

        return hive_memory.run(action="append", namespace=namespace, backend="json",
                               value={"text": summary, "meta": meta})
    except Exception:
        from realai.agentx.engine.memory import JsonFileMemoryAdapter

        root = Path(os.environ.get("REALAI_HOME") or Path(__file__).resolve().parents[3])
        d = root / "memory" / "hive"
        d.mkdir(parents=True, exist_ok=True)
        JsonFileMemoryAdapter(d / "memory.json").append(namespace, {"text": summary, "meta": meta})
        return {"ok": True, "backend": "json-direct", "namespace": namespace}


@dataclass
class Overmind:
    registry: HiveRegistry = field(default_factory=load_registry)
    teams: dict[str, Team] | None = None
    guardian: CapabilityGuardian = field(default_factory=CapabilityGuardian)
    dry_run: bool = True
    use_hive: bool | None = None  # None -> REALAI_AGENTX_USE_HIVE (default on)
    hive: HiveProvider | None = None

    def __post_init__(self) -> None:
        if self.teams is None:
            self.teams = load_teams(self.registry)
        self.router = AgentRouter()
        self.providers = ProviderRouter()

    def route(self, step: str, team_id: str | None = None) -> dict[str, Any]:
        team = (self.teams or {}).get(team_id or "")
        if team:
            own = team.owner_for(step)
            if own:
                return {"agent": own.owner, "reviewer": own.reviewer, "reason": f"ownership:{own.area}"}
            pool = {a: self.registry.manifests[a] for a in [team.lead, *team.members] if a in self.registry.manifests}
        else:
            pool = dict(self.registry.manifests)
        pool.pop("overmind", None)
        d = self.router.route(pool, step)
        return {"agent": d.agent_id, "reviewer": None, "reason": d.reason}

    def run(self, goal: str, team_id: str | None = None, memory_ns: str = "overmind") -> dict[str, Any]:
        steps = plan(goal)
        results = []
        for step in steps:
            r = self.route(step, team_id)
            raw = self.registry.raw.get(r["agent"], {"id": r["agent"]})
            access = self.guardian.check(raw)
            m = self.registry.manifests.get(r["agent"])
            tags = list(m.routing_tags) if m else []
            prov, fallback = pick_provider(tags, self.use_hive, self.hive)
            if fallback and self.hive is None and self.use_hive is not False:
                self.use_hive = False  # hive down: stop probing for the rest of this run
            # Placeholder stays dry-run; a live hive call is real (local model, no cloud keys).
            out = prov.complete(step, {"role": raw.get("role", ""), "tools": []}, self.dry_run if fallback else False)
            if out.get("error") and not fallback:
                prov = self.providers.select_provider(tags, ["local"])
                out = prov.complete(step, {"role": raw.get("role", ""), "tools": []}, self.dry_run)
                fallback = True
            results.append({"step": step, **r, "profile": access.profile, "provider": prov.name,
                            "fallback": fallback, "output": out.get("content") or out.get("response")})
        summary = summarize(results)
        mem = remember(memory_ns, summary, {"goal": goal[:200], "team": team_id, "ts": time.time()})
        return {"goal": goal, "team": team_id, "steps": results, "summary": summary, "memory": mem}
