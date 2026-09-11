"""Unified agents surface — hive + agentx + pipeline roles.

Authority:
  - Hive manifests: ``.github/agents/*.json`` (live hive archetypes)
  - Package gold: ``realai/agents`` (richer than root ``agents/`` twin)
  - Root ``agents/``: twin / docs / JSON; prefer realai.agents for Python

Dispatch flows through existing orch multi-agent + hive_router + bridge agents.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

ABILITY = {
    "id": "agents_surface",
    "name": "agents_surface",
    "type": "ability",
    "status": "LIVE",
    "source": ".github/agents + realai/agents + agents/",
    "dest": "abilities/agents_surface.py",
    "capabilities": [
        "hive",
        "agentx",
        "planner",
        "worker",
        "critic",
        "executor",
        "self_heal",
        "multi_agent",
    ],
    "secrets_policy": "none",
}

_ROOT = Path(__file__).resolve().parents[1]
_GITHUB = _ROOT / ".github" / "agents"
_PKG = _ROOT / "realai" / "agents"
_TOP = _ROOT / "agents"

LIVE_ROLES = {
    "hive": {"role": "Hive archetype roster (.github/agents)", "dispatch": "hive"},
    "overseer": {"role": "Hive Overseer", "dispatch": "hive_agent"},
    "coder": {"role": "Hive Coder", "dispatch": "hive_agent"},
    "architect": {"role": "Hive Architect", "dispatch": "hive_agent"},
    "analyst": {"role": "Hive Analyst", "dispatch": "hive_agent"},
    "memory": {"role": "Hive Memory", "dispatch": "hive_agent"},
    "governor": {"role": "Hive Governor", "dispatch": "hive_agent"},
    "router": {"role": "Hive Router", "dispatch": "hive_agent"},
    "planner": {"role": "Pipeline planner", "dispatch": "specialist"},
    "worker": {"role": "Pipeline worker", "dispatch": "specialist"},
    "critic": {"role": "Pipeline critic", "dispatch": "specialist"},
    "executor": {"role": "Pipeline executor", "dispatch": "specialist"},
    "self_heal": {"role": "Self-heal agent", "dispatch": "self_heal"},
    "multi": {"role": "Multi-agent pipeline", "dispatch": "multi"},
    "agentx": {"role": "agentx roster", "dispatch": "agentx"},
}


def _load_github_agents() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not _GITHUB.is_dir():
        return out
    for path in sorted(_GITHUB.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if isinstance(data, dict) and data.get("id"):
            item = dict(data)
            item["_path"] = str(path.relative_to(_ROOT)).replace("\\", "/")
            out.append(item)
    return out


def _package_inventory() -> Dict[str, Any]:
    def _top(path: Path) -> Dict[str, Any]:
        if not path.is_dir():
            return {"path": str(path), "exists": False}
        dirs = sorted(p.name for p in path.iterdir() if p.is_dir() and p.name != "__pycache__")
        files = sorted(p.name for p in path.iterdir() if p.is_file())
        return {
            "path": str(path),
            "exists": True,
            "dirs": dirs,
            "files": files[:60],
            "file_count": len(files),
            "dir_count": len(dirs),
        }

    return {
        "github_agents": _GITHUB.is_dir(),
        "realai_agents": _top(_PKG),
        "root_agents": _top(_TOP),
        "authority": "realai/agents + .github/agents (root agents/ is twin)",
    }


def _inventory() -> Dict[str, Any]:
    hive = _load_github_agents()
    pkg = _package_inventory()
    return {
        "ok": True,
        "ability": "agents_surface",
        "unified": True,
        "hive_mode": len(hive) >= 7,
        "hive_agents": [
            {
                "id": a.get("id"),
                "role": a.get("role"),
                "preferred_model": a.get("preferred_model"),
                "capabilities": (a.get("capabilities") or [])[:8],
                "path": a.get("_path"),
            }
            for a in hive
        ],
        "live_roles": [
            {"id": rid, "role": meta.get("role"), "dispatch": meta.get("dispatch")}
            for rid, meta in LIVE_ROLES.items()
        ],
        "packages": pkg,
        "endpoints": {
            "list_agents": "GET /v1/agents",
            "multi_agent": "POST /v1/multi-agent/run",
            "hive": "GET|POST /v1/hive",
            "tools": "agent_tools_* via /v1/tools/execute",
        },
        "note": "Use action=run agent=hive|overseer|coder|multi|self_heal|agentx",
    }


def _run_agent(agent_id: str, raw_input: str = "", ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ctx = dict(ctx or {})
    aid = (agent_id or "").strip().lower().replace("-", "_")
    if aid not in LIVE_ROLES and aid:
        # allow raw hive id
        LIVE_ROLES_ALIAS = {k.replace("_", "-"): k for k in LIVE_ROLES}
        aid = LIVE_ROLES.get(aid) and aid or LIVE_ROLES_ALIAS.get(agent_id.strip().lower(), aid)

    meta = LIVE_ROLES.get(aid) or {"role": agent_id, "dispatch": "hive_agent"}
    dispatch = str(meta.get("dispatch") or "hive_agent")
    out: Dict[str, Any] = {"ok": True, "agent": aid or agent_id, "role": meta.get("role"), "dispatch": dispatch}
    task = raw_input or str(ctx.get("task") or ctx.get("goal") or "agent status")

    if dispatch == "hive":
        try:
            from realai.v3_runtime_bridge import hive_agents_status

            out["result"] = hive_agents_status()
            out["via"] = "hive_agents_status"
        except Exception as e:
            out["ok"] = False
            out["error"] = str(e)
        return out

    if dispatch == "hive_agent":
        try:
            from realai.orchestration.hive_router import run_cycle

            out["result"] = run_cycle(task, agent=aid or "researcher", persist=bool(ctx.get("persist", True)))
            out["via"] = "hive_router.run_cycle"
        except Exception as e:
            out["ok"] = False
            out["error"] = str(e)
        return out

    if dispatch == "specialist":
        # map pipeline names onto hierarchical specialists
        mapping = {
            "planner": "researcher",
            "worker": "coder",
            "critic": "critic",
            "executor": "executor",
        }
        specialist = mapping.get(aid, aid)
        try:
            from abilities.hierarchical_specialists import run as hs

            out["result"] = hs(input=task, context={"agent": specialist})
            out["via"] = f"hierarchical_specialists:{specialist}"
        except Exception as e:
            # fallback multi-agent
            try:
                from realai.v3_runtime_bridge import run_multi_agent

                out["result"] = run_multi_agent(task, mode="pipeline")
                out["via"] = "multi_agent_fallback"
                out["specialist_error"] = str(e)
            except Exception as e2:
                out["ok"] = False
                out["error"] = f"{e}; {e2}"
        return out

    if dispatch == "multi":
        from realai.v3_runtime_bridge import run_multi_agent

        mode = str(ctx.get("mode") or "pipeline")
        out["result"] = run_multi_agent(task, mode=mode)
        out["via"] = "run_multi_agent"
        return out

    if dispatch == "self_heal":
        try:
            from realai.self_heal import status as heal_status

            out["result"] = heal_status()
            out["via"] = "self_heal.status"
        except Exception as e:
            out["ok"] = False
            out["error"] = str(e)
        return out

    if dispatch == "agentx":
        try:
            from realai.v3_runtime_bridge import list_agent_tools_agents

            out["result"] = list_agent_tools_agents(
                limit=int(ctx.get("limit") or 50),
                query=str(ctx.get("query") or task if task != "agent status" else ""),
            )
            out["via"] = "list_agent_tools_agents"
        except Exception as e:
            out["ok"] = False
            out["error"] = str(e)
        return out

    out["ok"] = False
    out["error"] = f"unknown_dispatch:{dispatch}"
    return out


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or "list").lower().strip()
    agent = str(ctx.get("agent") or ctx.get("id") or ctx.get("name") or "").strip()

    if action in {"list", "inventory", "status", "registry", "map", ""}:
        inv = _inventory()
        if agent:
            inv["selected"] = LIVE_ROLES.get(agent.lower().replace("-", "_")) or {"id": agent}
        return inv

    if action in {"run", "invoke", "dispatch", "cycle"}:
        raw = str(input or "")
        if not agent and raw:
            parts = raw.split(None, 1)
            agent = parts[0]
            raw = parts[1] if len(parts) > 1 else ""
        if not agent:
            agent = "hive"
        return _run_agent(agent, raw_input=raw, ctx=ctx)

    return {
        "ok": False,
        "error": f"unknown_action:{action}",
        "actions": ["list", "run", "cycle"],
        "known": sorted(LIVE_ROLES.keys()),
    }
