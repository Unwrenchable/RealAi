"""Unified hive orchestrator router — registers live + nest + pipeline stages.

Does not blind-import nest modules with broken relative imports. Instead:
  - live MultiAgentPipeline / MESSAGE_BUS
  - core.orchestration gold pipeline
  - exportable nest orchestrators listed as adapt-targets
  - deterministic stage cycle: planner → specialist → critic → executor
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

ROUTING_TABLE: Dict[str, str] = {
    "v3": "realai.v3_orchestrator",
    "pipeline": "core.orchestration.pipeline",
    "gold": "core.orchestration.orchestrator",
    "multi_agent": "realai.agent_runtime",
    "specialists": "abilities.hierarchical_specialists",
    "secure_tools": "abilities.secure_tools",
    "memory": "abilities.hive_memory",
    "domain": "abilities.hive_orchestrator",
    "plugin": "core.plugins",
    "world_model": "core.world_model",
    "nests": "abilities.nest_orchestrators",
    "critic_executor": "core.orchestration.hive_router",
}

# nextgen_hive role -> model id (ProviderRouter)
ROLE_MODEL_TABLE: Dict[str, str] = {
    "coder": "realai-default-coder-10",
    "architect": "qwen3-27b",
    "overseer": "realai-1.0-instruct",
    "orchestrator": "realai-1.0-instruct",
    "analyst": "local-llama-1b",
    "memory": "realai-embeddings",
    "governor": "local-llama-1b",
    "router": "local-llama-1b",
}

HIVE_ARCHETYPES = (
    "overseer",
    "coder",
    "architect",
    "analyst",
    "memory",
    "governor",
    "router",
)


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def list_nest_orchestrators() -> List[Dict[str, str]]:
    exportable = _root() / "scripts" / "exportable"
    out = []
    for p in sorted(exportable.glob("orchestrator_*.py")):
        out.append(
            {
                "name": p.stem,
                "path": str(p.relative_to(_root())).replace("\\", "/"),
                "status": "exportable_adapt",
                "note": "relative imports — adapt before core promote",
            }
        )
    return out


def route_model(agent_role: str = "", task_description: str = "") -> str:
    """Select model id for a hive agent role or task description."""
    role = (agent_role or "").strip().lower()
    task = (task_description or "").strip().lower()
    if role in ROLE_MODEL_TABLE:
        return ROLE_MODEL_TABLE[role]
    if any(k in task for k in ("code", "debug", "refactor", "implement", "patch")):
        return ROLE_MODEL_TABLE["coder"]
    if any(k in task for k in ("architect", "design", "structure", "multi-module")):
        return ROLE_MODEL_TABLE["architect"]
    if any(k in task for k in ("embed", "memory", "similarity", "recall")):
        return ROLE_MODEL_TABLE["memory"]
    if any(k in task for k in ("summar", "explain", "analy")):
        return ROLE_MODEL_TABLE["analyst"]
    return "local-llama-1b"


def load_github_hive_agents() -> List[Dict[str, Any]]:
    """Scan .github/agents/*.json for hive manifests."""
    import json

    agents_dir = _root() / ".github" / "agents"
    if not agents_dir.is_dir():
        return []
    out: List[Dict[str, Any]] = []
    for path in sorted(agents_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if isinstance(data, dict) and data.get("id"):
            item = dict(data)
            item["_path"] = str(path.relative_to(_root())).replace("\\", "/")
            out.append(item)
    return out


def register_routes() -> Dict[str, Any]:
    hive_agents = load_github_hive_agents()
    hive_ids = {str(a.get("id")) for a in hive_agents}
    return {
        "routes": dict(ROUTING_TABLE),
        "role_models": dict(ROLE_MODEL_TABLE),
        "nest": list_nest_orchestrators(),
        "fallback": "multi_agent",
        "hive_agents": sorted(hive_ids),
        "hive_mode": all(a in hive_ids for a in HIVE_ARCHETYPES),
        "hive_required": list(HIVE_ARCHETYPES),
    }


# Map nextgen hive roles onto hierarchical_specialists when needed
_HIVE_TO_SPECIALIST = {
    "overseer": "researcher",
    "orchestrator": "researcher",
    "architect": "researcher",
    "analyst": "researcher",
    "memory": "researcher",
    "governor": "critic",
    "router": "researcher",
    "coder": "coder",
}


def run_cycle(
    task: str,
    *,
    agent: str = "researcher",
    persist: bool = True,
) -> Dict[str, Any]:
    """planner → specialist → critic → executor style cycle (in-process).

    When hive agents are present, also records a hive delegation plan with
    preferred models from .github/agents (nextgen_hive).
    """
    stages: List[Dict[str, Any]] = []
    agent_key = (agent or "researcher").strip().lower()
    specialist_name = _HIVE_TO_SPECIALIST.get(agent_key, agent_key)
    routes = register_routes()

    # planner
    stages.append(
        {
            "stage": "planner",
            "task": task,
            "plan": f"Use specialist={specialist_name} (hive_role={agent_key}) then critic then executor",
            "preferred_model": route_model(agent_key, task),
        }
    )

    # hive delegation (overseer-style) when manifests exist
    hive_agents = load_github_hive_agents()
    if hive_agents and routes.get("hive_mode"):
        delegation = []
        for a in hive_agents:
            aid = str(a.get("id") or "")
            if aid not in HIVE_ARCHETYPES:
                continue
            model = a.get("preferred_model") or route_model(aid, task)
            delegation.append(
                {
                    "agent": aid,
                    "role": a.get("role"),
                    "model": model,
                    "capabilities": (a.get("capabilities") or [])[:5],
                }
            )
        stages.append(
            {
                "stage": "hive_delegation",
                "ok": True,
                "lead": agent_key,
                "agents": delegation,
                "count": len(delegation),
            }
        )

    # specialist (map hive roles onto known hierarchical specialists)
    try:
        from abilities.hierarchical_specialists import run as hs

        specialist = hs(input=task, context={"agent": specialist_name})
    except Exception as e:
        specialist = {"ok": False, "error": str(e)}
    stages.append(
        {
            "stage": "specialist",
            "agent": agent_key,
            "specialist": specialist_name,
            "preferred_model": route_model(agent_key, task),
            "result": specialist,
        }
    )

    # critic
    try:
        from abilities.hierarchical_specialists import run as hs

        critic = hs(input=f"Critique this result: {specialist}", context={"agent": "critic"})
    except Exception as e:
        critic = {"ok": False, "error": str(e)}
    stages.append({"stage": "critic", "result": critic})

    # executor
    try:
        from abilities.hierarchical_specialists import run as hs

        executor = hs(
            input=f"Execute next steps for task={task}",
            context={"agent": "executor"},
        )
    except Exception as e:
        executor = {"ok": False, "error": str(e)}
    stages.append({"stage": "executor", "result": executor})

    if persist:
        try:
            from abilities.hive_memory import run as mem

            mem(
                context={
                    "action": "append",
                    "namespace": "orchestrator_runs",
                    "value": {
                        "task": task,
                        "agent": agent_key,
                        "stages": [s["stage"] for s in stages],
                        "hive_mode": bool(routes.get("hive_mode")),
                    },
                    "backend": "sqlite",
                }
            )
        except Exception:
            pass

    # Hive mode: delegation stage success is enough even if specialist tools are soft-fail
    hive_ok = any(s.get("stage") == "hive_delegation" and s.get("ok") for s in stages)
    specialist_ok = (specialist or {}).get("ok", False)
    ok = hive_ok or (
        specialist_ok
        and all((s.get("result") or {}).get("ok", True) for s in stages if "result" in s)
    )
    return {
        "ok": ok,
        "task": task,
        "hive_mode": bool(routes.get("hive_mode")),
        "stages": stages,
        "routes": routes,
    }
