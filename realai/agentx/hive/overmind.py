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

    def _steps(self, goal: str, team: Team | None, live: bool) -> tuple[list[dict[str, str]], str]:
        if live and team and self.hive is not None and hasattr(self.hive, "chat"):
            from .agent_loop import model_plan

            steps = model_plan(self.hive.chat, goal, team.areas(), plan)
            if not (len(steps) == len(plan(goal)) and all(not st["area"] for st in steps)):
                return steps, "model"
            return steps, "rules-fallback"
        return [{"step": st, "area": ""} for st in plan(goal)], "rules"

    def run(self, goal: str, team_id: str | None = None, memory_ns: str = "overmind", run_id: str | None = None) -> dict[str, Any]:
        from functools import partial

        from . import events

        run_id = run_id or f"run-{int(time.time() * 1000)}"
        emit = partial(events.emit, run=run_id, team=team_id)
        emit("run.started", kind="team", goal=goal[:300])
        team = (self.teams or {}).get(team_id or "")
        if self.hive is None and self.use_hive is not False:
            self.hive = HiveProvider()
        live = bool(self.use_hive is not False and os.environ.get("REALAI_AGENTX_USE_HIVE", "1") != "0"
                    and self.hive is not None and self.hive.available())
        steps, planner = self._steps(goal, team, live)
        emit("plan.created", planner=planner, live=live, lead=team.lead if team else "overmind",
             steps=[{"step": x["step"][:200], "area": x.get("area", "")} for x in steps])
        root = team.workspace_root() if team else None
        max_steps = int(os.environ.get("REALAI_AGENT_MAX_STEPS", "8"))
        results = []
        for idx, st in enumerate(steps):
            step = st["step"]
            own = team.owner_for_area(st["area"]) if (team and st.get("area")) else None
            r = ({"agent": own.owner, "reviewer": own.reviewer, "reason": f"plan-area:{own.area}"}
                 if own else self.route(step, team_id))
            raw = self.registry.raw.get(r["agent"], {"id": r["agent"]})
            access = self.guardian.check(raw)
            m = self.registry.manifests.get(r["agent"])
            tags = list(m.routing_tags) if m else []
            ctx = {"role": raw.get("role", "") or r["agent"], "tools": []}
            rec: dict[str, Any] = {"step": step, "area": st.get("area", ""), **r, "profile": access.profile}
            lead = team.lead if team else "overmind"
            emit("handoff", src=lead, dst=r["agent"], area=st.get("area", ""), reason=r["reason"], index=idx)
            emit("step.started", agent=r["agent"], reviewer=r.get("reviewer"), index=idx, step=step[:200])
            read_ok = self.guardian.check(raw, required=["read_file", "list_dir", "grep_search"]).ok
            if live and root and read_ok:
                from .agent_loop import run_agent
                from .fs_tools import SafeFS

                out = run_agent(self.hive.chat, SafeFS(root), step, role=ctx["role"], max_steps=max_steps,
                                emit=emit, agent=r["agent"])
                rec.update(provider=self.hive.name, fallback=False, output=out["answer"],
                           tool_calls=out["tool_calls"], files_read=out["files_read"],
                           cited_ok=out["cited_ok"], cited_invented=out["cited_invented"],
                           grounding_retry=out["grounding_retry"])
            else:
                prov, fallback = (self.hive, False) if live else pick_provider(tags, False)
                o = prov.complete(step, ctx, self.dry_run if fallback else False)
                if o.get("error") and not fallback:
                    prov = self.providers.select_provider(tags, ["local"])
                    o = prov.complete(step, ctx, self.dry_run)
                    fallback = True
                rec.update(provider=prov.name, fallback=fallback, output=o.get("content") or o.get("response"))
            emit("step.finished", agent=r["agent"], index=idx, provider=rec.get("provider"), fallback=rec.get("fallback"),
                 files_read=rec.get("files_read", []), invented=rec.get("cited_invented", []),
                 output=str(rec.get("output") or "")[:1500])
            if r.get("reviewer"):
                emit("review", src=r["agent"], dst=r["reviewer"], index=idx, files=rec.get("files_read", []))
            results.append(rec)
        summary = summarize(results)
        emit("run.finished", kind="team", steps=len(results), summary=summary[:800])
        mem = remember(memory_ns, summary, {"goal": goal[:200], "team": team_id, "ts": time.time()})
        return {"goal": goal, "team": team_id, "planner": planner, "workspace": root,
                "steps": results, "summary": summary, "memory": mem}
