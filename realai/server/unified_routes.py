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

    return None
