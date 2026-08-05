"""Agents + orchestration adapter."""
from __future__ import annotations
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def list_agent_modules() -> dict[str, str]:
    agents = ROOT / "core" / "agents"
    out = {}
    if agents.exists():
        for p in agents.glob("*.py"):
            if p.name != "__init__.py":
                out[p.stem] = str(p.relative_to(ROOT)).replace("\\", "/")
    skills = ROOT / "modules" / "agents_skills"
    if skills.exists():
        out["agents_skills_pack"] = str(skills.relative_to(ROOT)).replace("\\", "/")
    return out


def list_orchestration_modules() -> dict[str, str]:
    orch = ROOT / "core" / "orchestration"
    out = {}
    if orch.exists():
        for p in orch.glob("*.py"):
            if p.name != "__init__.py":
                out[p.stem] = str(p.relative_to(ROOT)).replace("\\", "/")
    mod = ROOT / "modules" / "orchestrators"
    if mod.exists():
        out["orchestrators_pack"] = str(mod.relative_to(ROOT)).replace("\\", "/")
    return out


def agents_status() -> dict[str, Any]:
    return {"agents": list_agent_modules(), "orchestration": list_orchestration_modules()}
