"""Hive router — role→model routing, nest index, and cycle runner.

Replaces the broken self-import shim so ``ability.hive_orchestrator`` / ``hive_run`` work locally.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

ROLE_MODEL_TABLE: Dict[str, str] = {
    "coder": "realai-default-coder-10",
    "architect": "qwen3-27b",
    "overseer": "realai-1.0-instruct",
    "orchestrator": "realai-1.0-instruct",
    "analyst": "local-llama-1b",
    "memory": "realai-embeddings",
    "governor": "local-llama-1b",
    "router": "local-llama-1b",
    "researcher": "realai-1.0-instruct",
    "executor": "realai-default-coder-10",
    "critic": "local-llama-1b",
    "creative": "realai-1.0-instruct",
}

_ARCHETYPES = (
    "overseer",
    "coder",
    "architect",
    "analyst",
    "memory",
    "governor",
    "router",
)


# Stage order of the multi-agent pipeline run_multi_agent executes (agents/agent_runtime.MultiAgentPipeline.STAGES).
PIPELINE_STAGES = ("planner", "researcher", "critic", "executor", "synthesizer")


def _product_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_github_hive_agents() -> List[Dict[str, Any]]:
    """Load hive role manifests via the canonical agentx loader (AgentManifestLoader + converters).

    Returns the legacy dict shape (``{"id": ..., ...}``) so register_routes keeps working.
    Falls back to the previous bridge / glob loader if agentx is unavailable.
    """
    try:
        from realai.agentx.hive.registry import load_registry

        roles = load_registry(include_catalog=False).hive_role_dicts()
        if roles:
            return roles
    except Exception:
        pass
    try:
        from realai.v3_runtime_bridge import hive_agents_status

        # Prefer bridge loader when available
        from realai.orchestration import v3_runtime_bridge as br

        return list(br._load_github_hive_agents())  # type: ignore[attr-defined]
    except Exception:
        pass
    root = _product_root() / ".github" / "agents"
    if not root.is_dir():
        return []
    import json

    out: List[Dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if isinstance(data, dict) and data.get("id"):
            out.append(data)
    return out


def route_model(agent_role: str = "", task_description: str = "") -> str:
    try:
        from realai.v3_runtime_bridge import route_model as _rm

        return _rm(agent_role, task_description)
    except Exception:
        role = (agent_role or "").strip().lower()
        return ROLE_MODEL_TABLE.get(role, "realai-default-coder")


def register_routes() -> Dict[str, Any]:
    """Register / report hive role→model routes."""
    agents = load_github_hive_agents()
    by_id = {str(a.get("id")): a for a in agents if a.get("id")}
    present = [a for a in _ARCHETYPES if a in by_id]
    missing = [a for a in _ARCHETYPES if a not in by_id]
    return {
        "ok": len(missing) == 0,
        "hive_mode": len(missing) == 0,
        "hive_agents": present,
        "missing": missing,
        "fallback": "multi_agent",
        "role_models": dict(ROLE_MODEL_TABLE),
        "routing_sample": {r: route_model(r) for r in _ARCHETYPES},
        "count": len(by_id),
    }


def list_nest_orchestrators() -> Dict[str, Any]:
    """Index nest/exportable orchestrator salvage + live ability surface."""
    root = _product_root()
    exportable = root / "scripts" / "exportable"
    files = sorted(p.name for p in exportable.glob("orchestrator_*.py")) if exportable.is_dir() else []
    nests_doc = root / "modules" / "orchestrators" / "NEST_ORCHESTRATORS.md"
    return {
        "ok": True,
        "exportable_dir": str(exportable),
        "orchestrators": files,
        "count": len(files),
        "index_doc": str(nests_doc) if nests_doc.is_file() else None,
        "live_surface": "ability.nest_orchestrators + ability.hive_orchestrator",
    }


def run_cycle(
    task: str,
    agent: str = "researcher",
    persist: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Run a hive cycle: prefer multi-agent pipeline, fall back to single chat.

    ``dry_run=True`` resolves routes and the model exactly as a real cycle would, then returns the plan
    (pipeline stages, model, routes) WITHOUT calling the pipeline, the network, or persisting anything.
    Default False keeps live behaviour unchanged."""
    task = (task or "hive status").strip()
    agent = (agent or "researcher").strip()
    routes = register_routes()
    model = route_model(agent, task)

    # Status-only fast path
    if task.lower() in {"hive status", "status", "routes", "info"}:
        return {
            "ok": True,
            "action": "status",
            "agent": agent,
            "model": model,
            "routes": routes,
            "nests": list_nest_orchestrators(),
            "persist": persist,
        }

    if dry_run:
        return {
            "ok": True,
            "action": "dry_run",
            "agent": agent,
            "model": model,
            "persist": False,
            "routes": {"hive_mode": routes.get("hive_mode"), "fallback": "multi_agent",
                       "missing": routes.get("missing")},
            "plan": {"would_call": "run_multi_agent", "mode": "pipeline", "stages": list(PIPELINE_STAGES),
                     "task": f"[hive:{agent}] {task}"[:300]},
        }

    try:
        from realai.v3_runtime_bridge import run_multi_agent

        result = run_multi_agent(f"[hive:{agent}] {task}", mode="pipeline")
        return {
            "ok": True,
            "action": "cycle",
            "agent": agent,
            "model": model,
            "persist": persist,
            "routes": {"hive_mode": routes.get("hive_mode"), "fallback": "multi_agent"},
            "result": result,
        }
    except Exception as e:
        # Last resort: direct chat
        try:
            import json
            import urllib.request

            body = json.dumps(
                {
                    "model": "realai-default-coder",
                    "messages": [
                        {
                            "role": "system",
                            "content": f"You are RealAI hive agent '{agent}'. Be concise.",
                        },
                        {"role": "user", "content": task},
                    ],
                    "max_tokens": 256,
                }
            ).encode()
            req = urllib.request.Request(
                "http://127.0.0.1:8001/v1/chat/completions",
                data=body,
                headers={"Content-Type": "application/json", "X-RealAI-Tools": "off"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
            text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            return {
                "ok": True,
                "action": "cycle_chat_fallback",
                "agent": agent,
                "model": model,
                "result": {"final_output": text},
                "multi_agent_error": str(e),
            }
        except Exception as e2:
            return {
                "ok": False,
                "action": "cycle",
                "agent": agent,
                "error": str(e),
                "fallback_error": str(e2),
            }


# --- ability entrypoint (spine 1b) -----------------------------------------
# ``ability.hive_orchestrator`` / ``ability.hive`` resolve here; behaviour matches the
# former abilities/hive_orchestrator.py wrapper (archive verdict).
ABILITY = {
    "id": "hive_orchestrator",
    "name": "hive_orchestrator",
    "type": "ability",
    "status": "LIVE",
    "source": "realai.orchestration.hive_router",
    "dest": "realai/orchestration/hive_router.py",
    "capabilities": ["routing", "nested_orchestrators", "planner_specialist_critic_executor"],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or "cycle").lower()
    if action in {"routes", "register", "list"}:
        return {"ok": True, "ability": "hive_orchestrator", **register_routes()}
    if action in {"nest", "exportable"}:
        return {"ok": True, "ability": "hive_orchestrator", "nest": list_nest_orchestrators()}
    task = input or str(ctx.get("task") or "hive status")
    agent = str(ctx.get("agent") or "researcher")
    result = run_cycle(task, agent=agent, persist=bool(ctx.get("persist", True)))
    result["ability"] = "hive_orchestrator"
    return result
