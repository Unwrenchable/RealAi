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


def _product_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_github_hive_agents() -> List[Dict[str, Any]]:
    """Load `.github/agents/*.json` hive manifests."""
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
) -> Dict[str, Any]:
    """Run a hive cycle: prefer multi-agent pipeline, fall back to single chat."""
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
