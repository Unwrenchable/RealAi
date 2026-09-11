"""Unified ``modules`` surface — living non-core product packages.

Authority: repo-root ``modules/`` (``import modules.organs``).
``realai/modules`` holds identical twin dirs; PyTorch QAT stubs were quarantined.
"""

from __future__ import annotations

import importlib
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

ABILITY = {
    "id": "modules_surface",
    "name": "modules_surface",
    "type": "ability",
    "status": "LIVE",
    "source": "modules/ (+ realai/modules twin)",
    "dest": "abilities/modules_surface.py",
    "capabilities": [
        "organs",
        "agents_advanced",
        "desktop_unique",
        "orchestrators",
        "self_improvement",
        "agents_skills",
        "training",
    ],
    "secrets_policy": "none",
}

_ROOT = Path(__file__).resolve().parents[1]
_TOP = _ROOT / "modules"
_TWIN = _ROOT / "realai" / "modules"

MODULES_REGISTRY: Dict[str, Dict[str, Any]] = {
    "organs": {
        "module": "modules.organs",
        "role": "Synthetic organs hive (45 organs)",
        "dispatch": "organs",
        "aliases": ["organs_hive"],
    },
    "agents_advanced": {
        "module": "modules.agents_advanced",
        "role": "Advanced agents (overmind, code_engineer, …)",
        "dispatch": "agents_advanced",
        "aliases": ["overmind"],
    },
    "agents_skills": {
        "module": "modules.agents_skills",
        "role": "Agent skills pack",
        "dispatch": "status",
    },
    "desktop_unique": {
        "module": "modules.desktop_unique",
        "role": "Desktop lambda / unique desktop modules",
        "dispatch": "desktop",
        "aliases": ["desktop", "lambda"],
    },
    "orchestrators": {
        "module": "modules.orchestrators",
        "role": "Nest/exportable orchestrator dump under modules",
        "dispatch": "orchestrators",
        "aliases": ["nests"],
    },
    "self_improvement": {
        "module": "modules.self_improvement",
        "role": "Self-improvement helpers under modules",
        "dispatch": "status",
    },
    "training": {
        "module": "modules.training",
        "role": "Training package slot (may be empty)",
        "dispatch": "status",
    },
}


def _resolve(name: str) -> Optional[str]:
    key = (name or "").strip().lower().replace("-", "_")
    if not key:
        return None
    if key in MODULES_REGISTRY:
        return key
    for mid, meta in MODULES_REGISTRY.items():
        if key in [str(a).lower() for a in (meta.get("aliases") or [])]:
            return mid
        if key == str(meta.get("module") or "").rsplit(".", 1)[-1].lower():
            return mid
    return None


def _tree_info(path: Path) -> Dict[str, Any]:
    if not path.is_dir():
        return {"path": str(path), "exists": False}
    dirs = sorted(p.name for p in path.iterdir() if p.is_dir() and p.name != "__pycache__")
    files = sorted(p.name for p in path.iterdir() if p.is_file())
    return {
        "path": str(path),
        "exists": True,
        "dirs": dirs,
        "files": files,
        "dir_count": len(dirs),
        "file_count": len(files),
    }


def _inventory() -> Dict[str, Any]:
    mods = []
    for mid, meta in MODULES_REGISTRY.items():
        path = _TOP / mid
        twin = _TWIN / mid
        mods.append(
            {
                "id": mid,
                "role": meta.get("role"),
                "module": meta.get("module"),
                "present": path.is_dir(),
                "twin_present": twin.is_dir(),
                "path": str(path),
            }
        )
    return {
        "ok": True,
        "ability": "modules_surface",
        "unified": True,
        "authority": "C:\\RealAI-clean\\modules (import modules.*)",
        "packages": {
            "modules": _tree_info(_TOP),
            "realai_modules_twin": _tree_info(_TWIN),
        },
        "modules": mods,
        "note": (
            "Product dirs are live under modules/. realai/modules is a twin. "
            "Torch QAT stubs quarantined to _quarantine/modules_unify_20260830."
        ),
        "already_wired": [
            "ability.organs_hive",
            "ability.overmind_runner",
            "ability.code_engineer_agent",
            "ability.desktop_lambda_*",
            "craft organs / hive organs",
        ],
    }


def _run(mid: str, raw_input: str = "", ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ctx = dict(ctx or {})
    meta = MODULES_REGISTRY[mid]
    out: Dict[str, Any] = {
        "ok": True,
        "module_id": mid,
        "module": meta.get("module"),
        "role": meta.get("role"),
    }
    dispatch = str(meta.get("dispatch") or "status")

    if dispatch == "organs":
        try:
            from modules.organs import hive_status, list_organs

            out["result"] = {
                "hive_status": hive_status(),
                "organ_ids": list_organs()[:50] if callable(list_organs) else None,
            }
            # optional pipeline
            action = str(ctx.get("action") or "").lower()
            if action in {"pipeline", "run"} or raw_input:
                try:
                    from modules.organs.request_path import run_organ_pipeline, living_stack_status

                    out["result"]["living_stack"] = living_stack_status()
                    if raw_input:
                        out["result"]["pipeline"] = run_organ_pipeline(raw_input)
                except Exception as e:
                    out["result"]["pipeline_error"] = str(e)
            out["via"] = "modules.organs"
        except Exception as e:
            out["ok"] = False
            out["error"] = str(e)
            out["trace"] = traceback.format_exc()[-400:]
        return out

    if dispatch == "agents_advanced":
        # Prefer ability wrappers for overmind / code engineer
        target = str(ctx.get("ability") or raw_input or "overmind_runner").strip() or "overmind_runner"
        if target.lower() in {"status", "list", "agents_advanced"}:
            try:
                mod = importlib.import_module("modules.agents_advanced")
                out["result"] = {
                    "exports": [n for n in dir(mod) if not n.startswith("_")][:40],
                    "path": getattr(mod, "__file__", None),
                }
                # list submodule files
                p = _TOP / "agents_advanced"
                out["result"]["files"] = sorted(x.name for x in p.glob("*.py")) if p.is_dir() else []
                out["via"] = "modules.agents_advanced"
            except Exception as e:
                out["ok"] = False
                out["error"] = str(e)
            return out
        from realai.v3_runtime_bridge import execute_registry_tool

        aid = target if target.startswith("ability.") else f"ability.{target}"
        out["result"] = execute_registry_tool(aid, {"input": raw_input, "context": ctx})
        out["via"] = aid
        return out

    if dispatch == "desktop":
        target = str(ctx.get("ability") or "desktop_lambda_chat")
        from realai.v3_runtime_bridge import execute_registry_tool

        aid = target if target.startswith("ability.") else f"ability.{target}"
        out["result"] = execute_registry_tool(aid, {"input": raw_input, "context": ctx})
        out["via"] = aid
        return out

    if dispatch == "orchestrators":
        # Point at nest surface rather than competing servers
        from realai.v3_runtime_bridge import execute_registry_tool

        out["result"] = execute_registry_tool(
            "ability.nest_orchestrators",
            {"action": "list", "input": raw_input},
        )
        out["via"] = "ability.nest_orchestrators"
        out["note"] = "modules/orchestrators is a nest dump; dispatch via nest_orchestrators"
        return out

    # generic status
    try:
        mod = importlib.import_module(str(meta["module"]))
        out["result"] = {
            "exports": [n for n in dir(mod) if not n.startswith("_")][:40],
            "file": getattr(mod, "__file__", None),
        }
        out["via"] = meta["module"]
    except Exception as e:
        path = _TOP / mid
        out["result"] = {
            "import_error": str(e),
            "path": str(path),
            "exists": path.exists(),
            "files": sorted(p.name for p in path.iterdir()) if path.is_dir() else [],
        }
        out["via"] = "filesystem"
    return out


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or "list").lower().strip()
    name = str(ctx.get("module") or ctx.get("id") or ctx.get("name") or "").strip()

    if action in {"list", "inventory", "status", "registry", "map", ""}:
        inv = _inventory()
        if name:
            mid = _resolve(name)
            if mid:
                inv["selected"] = next(m for m in inv["modules"] if m["id"] == mid)
        return inv

    if action in {"run", "invoke", "dispatch"}:
        raw = str(input or "")
        mid = _resolve(name) if name else None
        if not mid and raw:
            parts = raw.split(None, 1)
            mid = _resolve(parts[0])
            raw = parts[1] if len(parts) > 1 else ""
        if not mid:
            return {
                "ok": False,
                "error": "module_id_required",
                "known": sorted(MODULES_REGISTRY.keys()),
                "hint": "action=run module=organs|agents_advanced|desktop_unique|orchestrators",
            }
        return _run(mid, raw_input=raw, ctx=ctx)

    return {
        "ok": False,
        "error": f"unknown_action:{action}",
        "actions": ["list", "run"],
        "known": sorted(MODULES_REGISTRY.keys()),
    }
