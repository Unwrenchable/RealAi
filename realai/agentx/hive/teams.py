"""Team files -> AgentGraph.

Team file (JSON), e.g. data/teams/vault77/team.json::

  {"id": "vault77", "lead": "vault-77-overseer",
   "members": [{"id": "fullstack-dev", "file": "agents/fullstack-dev.md"}, ...],
   "ownership": [{"area": "backend", "owner": "fullstack-dev", "reviewer": "vault-77-overseer",
                  "keywords": ["express", "api"]}],
   "handoffs": [{"from": "vault-77-overseer", "to": "fullstack-dev", "condition": "backend"}],
   "memory": "memory.md"}
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from realai.agent_runtime.agent_runtime import AgentEdge, AgentGraph, AgentNode

from .converters import agent_md_to_manifest
from .registry import DATA, HiveRegistry

TEAMS_DIR = DATA / "teams"


@dataclass
class Ownership:
    area: str
    owner: str
    reviewer: str | None = None
    keywords: list[str] = field(default_factory=list)


@dataclass
class Team:
    id: str
    lead: str
    members: list[str]
    ownership: list[Ownership]
    handoffs: list[dict[str, Any]]
    path: Path
    memory: str | None = None
    root: str | None = None  # read-only workspace root for fs tools (team.json "workspace.root")

    def workspace_root(self) -> str | None:
        """Env REALAI_TEAM_ROOT_<ID> overrides team.json; None when unset or missing."""
        env = os.environ.get("REALAI_TEAM_ROOT_" + re.sub(r"\W", "_", self.id).upper())
        r = env or self.root
        return r if r and Path(r).is_dir() else None

    def areas(self) -> list[str]:
        return [o.area for o in self.ownership]

    def owner_for_area(self, area: str) -> Ownership | None:
        return next((o for o in self.ownership if o.area == area), None)

    def owner_for(self, text: str) -> Ownership | None:
        low = text.lower()
        best, score = None, 0
        for o in self.ownership:
            s = sum(3 for k in o.keywords if k.lower() in low) + (2 if o.area.lower() in low else 0)
            if s > score:
                best, score = o, s
        return best

    def graph(self) -> AgentGraph:
        g = AgentGraph()
        for m in [self.lead, *self.members]:
            g.add_node(AgentNode(agent_id=m, task_template="{input}"))
        for h in self.handoffs:
            g.add_edge(AgentEdge(from_node=h["from"], to_node=h["to"], condition=h.get("condition")))
        return g

    def validate(self) -> list[str]:
        ids = {self.lead, *self.members}
        errs = []
        for h in self.handoffs:
            for k in ("from", "to"):
                if h.get(k) not in ids:
                    errs.append(f"{self.id}: handoff {k}={h.get(k)!r} is not a member")
        for o in self.ownership:
            for who in (o.owner, o.reviewer):
                if who and who not in ids:
                    errs.append(f"{self.id}: ownership {o.area} references unknown {who!r}")
        return errs


def load_team(path: Path, registry: HiveRegistry | None = None) -> Team:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    members: list[str] = []
    for m in data.get("members", []):
        mid = m["id"] if isinstance(m, dict) else str(m)
        members.append(mid)
        if registry is not None and isinstance(m, dict) and m.get("file"):
            f = path.parent / m["file"]
            if f.is_file():
                raw = agent_md_to_manifest(f, agent_id=mid)
                if raw:
                    registry.add(raw)
    if registry is not None and data.get("lead_file"):
        f = path.parent / data["lead_file"]
        if f.is_file():
            raw = agent_md_to_manifest(f, agent_id=data["lead"])
            if raw:
                registry.add(raw)
    return Team(
        id=data["id"], lead=data["lead"], members=[m for m in members if m != data["lead"]],
        ownership=[Ownership(o["area"], o["owner"], o.get("reviewer"), list(o.get("keywords", [])))
                   for o in data.get("ownership", [])],
        handoffs=list(data.get("handoffs", [])), path=path, memory=data.get("memory"),
        root=(data.get("workspace") or {}).get("root") if isinstance(data.get("workspace"), dict) else None,
    )


def load_teams(registry: HiveRegistry | None = None, teams_dir: Path | None = None) -> dict[str, Team]:
    root = Path(teams_dir or TEAMS_DIR)
    return {t.id: t for t in (load_team(p, registry) for p in sorted(root.glob("*/team.json")))}
