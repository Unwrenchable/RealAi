"""Opt-in routes promoted from RealAi-unified 763a4c2 (realai/server/router.py).

Additive only: consulted by ``dispatch_request`` after every existing route
misses, and only when REALAI_UNIFIED_ROUTES=1. Default behaviour (404) is unchanged.
Status: PARTIAL. No network, no outside keys; scans read-only inside REALAI_HOME.

Routes:
  POST /v1/self/evolve                 (dry-run unless REALAI_SELF_EVOLVING=1)
  POST /v1/synthetic/organisms         (+ aliases /v1/synthetic/organism, /v1/synthetic-organism[s])
  GET  /v1/synthetic/organisms
  GET  /v1/synthetic/organisms/{id}
  POST /v1/curiosity
  POST /v1/archeology
  POST /v1/workspace/catalog
  POST /v1/tools/route
  POST /v1/tools/execute               (audited envelope; does not run the tool)
  GET  /v1/skills, GET /v1/agents
  GET  /v1/plugins, POST /v1/plugins/execute  (first-party allow-list only)
  GET  /v1/world/state, POST /v1/world/observe
  POST /v1/reflection/analyze
  POST /v1/synthesis/knowledge, POST /v1/agents/orchestrate  (local RealAI, no network)
/health gains a ``runtime`` block when enabled (see ``runtime_summary``).
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

_CREATE_PATHS = {
    "/v1/synthetic/organism",
    "/v1/synthetic/organisms",
    "/v1/synthetic-organism",
    "/v1/synthetic-organisms",
}
JSON = "application/json"


def enabled() -> bool:
    return os.environ.get("REALAI_UNIFIED_ROUTES", "").strip().lower() in {"1", "true", "yes", "on"}


def _str(payload: Dict[str, Any], key: str) -> Optional[str]:
    val = payload.get(key)
    return val.strip() if isinstance(val, str) and val.strip() else None


def _bad(msg: str, code: int = 400) -> Tuple[int, Dict[str, Any], str]:
    return code, {"error": {"message": msg}}, JSON


def dispatch(method: str, path: str, payload: Any = None) -> Optional[Tuple[int, Dict[str, Any], str]]:
    """Return (status, body, content_type) or None when the route is not ours."""
    if not enabled():
        return None
    body: Dict[str, Any] = payload if isinstance(payload, dict) else {}

    if method == "POST" and path == "/v1/self/evolve":
        from realai.plugins.self_evolving import evolve

        text = _str(body, "text")
        if not text:
            return _bad("text is required.")
        return 200, {"ok": True, "self_evolution": evolve(text, _str(body, "tool_name"))}, JSON

    if path in _CREATE_PATHS or path.startswith("/v1/synthetic/organisms/") or path in {"/v1/curiosity", "/v1/archeology"}:
        from modules.organs.synthetic_organs import get_runtime

        rt = get_runtime()
        if method == "POST" and path in _CREATE_PATHS:
            name, species = _str(body, "name"), _str(body, "species")
            if not name:
                return _bad("name is required.")
            if not species:
                return _bad("species is required.")
            prompt = _str(body, "prompt") or _str(body, "description") or ""
            target = _str(body, "target")
            return 200, {
                "ok": True,
                "organism": rt.create_organism(name, species, prompt),
                "curiosity": rt.curate_curiosity(target=target, prompt=prompt),
                "archeology": rt.archeology(target=target),
            }, JSON
        if method == "GET" and path == "/v1/synthetic/organisms":
            return 200, {"object": "list", "data": rt.list_organisms()}, JSON
        if method == "GET" and path.startswith("/v1/synthetic/organisms/"):
            org = rt.get_organism(path[len("/v1/synthetic/organisms/"):])
            if not org:
                return _bad("organism not found.", 404)
            return 200, {"object": "synthetic_organism", "data": org}, JSON
        if method == "POST" and path == "/v1/curiosity":
            return 200, rt.curate_curiosity(target=_str(body, "target"), prompt=_str(body, "prompt")), JSON
        if method == "POST" and path == "/v1/archeology":
            return 200, rt.archeology(target=_str(body, "target")), JSON

    if method == "POST" and path == "/v1/workspace/catalog":
        from realai.plugins.workspace_info import workspace_catalog

        out = workspace_catalog(_str(body, "root"))
        return (200 if out.get("ok") else 400), out, JSON

    if method == "POST" and path == "/v1/tools/route":
        from realai.plugins.tool_router import route

        text = _str(body, "text")
        if not text:
            return _bad("text is required.")
        allowed = body.get("allowed_tools") if isinstance(body.get("allowed_tools"), list) else None
        return 200, route(text, allowed, _str(body, "provider") or "local"), JSON

    return _dispatch_runtime(method, path, body)



# --- Ported from RealAi-unified router.py (handlers live lacked) -----------------

RUNTIME_ROLES = ("critic", "executor", "planner", "safety", "synthesizer", "worker")
EXTRA_PLUGINS = ("workspace_info", "tool_router")
_BELIEF = None


def _plugin_names():
    from realai.plugins import list_first_party

    return list(list_first_party()) + [p for p in EXTRA_PLUGINS]


def _load_plugin(name: str):
    from realai.plugins import load_first_party

    return load_first_party(name)


def _world():
    global _BELIEF
    from realai import world_model as wm

    if _BELIEF is None:
        _BELIEF = wm.BeliefUpdater()
    return wm, _BELIEF


def _world_facts():
    wm, _ = _world()
    out = {}
    for key, entry in wm.WORLD_STATE.all_facts().items():
        out[key] = entry["value"] if isinstance(entry, dict) and "value" in entry else entry
    return out


def _world_payload():
    wm, _ = _world()
    return {"facts": _world_facts(), "observations": len(getattr(wm.WORLD_STATE, "_observations", []))}


def _local_model():
    from realai import RealAI

    return RealAI(model_name="realai-1.0", provider="local", use_local=True)


def runtime_summary() -> Dict[str, Any]:
    from .tools_runtime import TOOLS

    plugins = _plugin_names()
    return {
        "memory": {"enabled": True},
        "plugins": {"enabled": True, "count": len(plugins), "names": plugins},
        "world": {"enabled": True, "facts": _world_facts()},
        "tools": {"enabled": True, "count": len(TOOLS.list_tools())},
        "skills": {"enabled": True, "count": len(RUNTIME_ROLES), "names": list(RUNTIME_ROLES)},
        "agents": {"enabled": True, "count": len(RUNTIME_ROLES), "names": list(RUNTIME_ROLES)},
    }


def _dispatch_runtime(method: str, path: str, body: Dict[str, Any]):
    if method == "POST" and path == "/v1/tools/execute":
        from .tools_runtime import TOOLS

        name = _str(body, "name")
        if not name:
            return _bad("name is required.")
        params = body.get("params", {})
        if not isinstance(params, dict):
            return _bad("params must be an object when provided.")
        result = TOOLS.execute(name, params=params, actor=_str(body, "actor") or "system")
        return 200, {"ok": True, "tool": name, "result": result}, JSON

    if method == "GET" and path in {"/v1/skills", "/v1/agents"}:
        kind = "skill" if path.endswith("skills") else "agent"
        data = [{"name": n, "kind": kind, "description": f"{n} runtime {kind}"} for n in RUNTIME_ROLES]
        return 200, {"object": "list", "data": data}, JSON

    if method == "GET" and path == "/v1/plugins":
        data = []
        for name in _plugin_names():
            try:
                mod = _load_plugin(name)
                doc = (mod.__doc__ or "").strip().splitlines()
                data.append({"name": name, "metadata": {"description": doc[0] if doc else "", "module": mod.__name__}})
            except Exception as exc:  # report, don't hide, broken plugins
                data.append({"name": name, "metadata": {"error": str(exc)}})
        return 200, {"object": "list", "data": data}, JSON

    if method == "POST" and path == "/v1/plugins/execute":
        name = _str(body, "name")
        if not name:
            return _bad("name is required.")
        if name not in _plugin_names():
            return _bad("Unknown plugin.")
        mod = _load_plugin(name)
        register = getattr(mod, "register", None)
        metadata = register(type("DummyModel", (), {})()) if callable(register) else {}
        return 200, {"ok": True, "plugin": name, "metadata": metadata if isinstance(metadata, dict) else {}, "data": body.get("data", {})}, JSON

    if method == "GET" and path == "/v1/world/state":
        return 200, {"object": "world_state", "world": _world_payload()}, JSON

    if method == "POST" and path == "/v1/world/observe":
        content = _str(body, "content")
        if not content:
            return _bad("content is required.")
        wm, belief = _world()
        obs = wm.WORLD_STATE.observe(content, source=_str(body, "source") or "api")
        belief.update(wm.WORLD_STATE, obs)
        plan = wm.PLANNING_ENGINE.plan(content, wm.WORLD_STATE, max_steps=3)
        wm.GOAL_TRACKER.add_goal(content)
        return 200, {"observed": True, "world": _world_payload(), "plan": plan}, JSON

    if method == "POST" and path == "/v1/reflection/analyze":
        text = _str(body, "text")
        if not text:
            return _bad("text is required.")
        words = " ".join(seg.strip() for seg in text.split(".") if seg.strip()).split()
        summary = " ".join(words[:20]) + ("..." if len(words) > 20 else "")
        return 200, {"reflection": {"summary": summary, "goal": _str(body, "goal") or "improve understanding",
                                    "model": "realai-1.0", "focus": "local-runtime-reflection"}}, JSON

    if method == "POST" and path == "/v1/synthesis/knowledge":
        facts = body.get("facts")
        if not isinstance(facts, list) or not facts:
            return _bad("facts must be a non-empty list.")
        result = _local_model().synthesize_knowledge(facts)
        result = result if isinstance(result, dict) else {"synthesis": str(result)}
        return 200, {"synthesis": {"summary": result.get("synthesis") or result.get("summary") or str(result),
                                   "connections": result.get("connections", []),
                                   "topics": result.get("topics", facts)}}, JSON

    if method == "POST" and path == "/v1/agents/orchestrate":
        task = _str(body, "task")
        if not task:
            return _bad("task is required.")
        agents = body.get("agents") or ["planner", "executor"]
        if not isinstance(agents, list):
            return _bad("agents must be a non-empty list when provided.")
        result = _local_model().orchestrate_agents(task, agent_roles=agents)
        result = result if isinstance(result, dict) else {}
        return 200, {"orchestration": {"task": task, "agents": agents, "status": result.get("status", "success"),
                                       "result": result}}, JSON
