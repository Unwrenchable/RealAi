"""Unified ``core`` package surface (importable as ``core`` via realai/ on PYTHONPATH).

Live home: ``realai/core``.
HTTP orch gold: ``realai.orchestration`` (core.orchestration.v3/hive_router are shims).
"""

from __future__ import annotations

import importlib
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

ABILITY = {
    "id": "core_surface",
    "name": "core_surface",
    "type": "ability",
    "status": "LIVE",
    "source": "realai/core",
    "dest": "abilities/core_surface.py",
    "capabilities": [
        "agents",
        "tools",
        "security",
        "voice",
        "web3",
        "memory",
        "inference",
        "training",
        "identity",
        "safety",
        "orchestration",
    ],
    "secrets_policy": "none",
}

_ROOT = Path(__file__).resolve().parents[1]
_CORE = _ROOT / "realai" / "core"

# Subsystems that belong in core and how to probe them.
CORE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "package": {
        "module": "core",
        "role": "Core package root",
        "kind": "PACKAGE",
        "path": "__init__.py",
    },
    "agents": {
        "module": "core.agents",
        "role": "Specialist agents registry (researcher/coder/critic/…)",
        "kind": "LIVE_SUBPKG",
        "path": "agents",
        "dispatch": "agents",
    },
    "tools": {
        "module": "core.tools",
        "role": "ToolRegistry + code/file/web/web3 tools",
        "kind": "LIVE_SUBPKG",
        "path": "tools",
        "dispatch": "tools",
    },
    "security": {
        "module": "core.security",
        "role": "Sandbox / permissions",
        "kind": "LIVE_SUBPKG",
        "path": "security",
        "dispatch": "security",
    },
    "voice": {
        "module": "core.voice",
        "role": "ASR/TTS voice backends",
        "kind": "LIVE_SUBPKG",
        "path": "voice",
        "dispatch": "status",
    },
    "web3": {
        "module": "core.web3",
        "role": "Web3 / Solana backends",
        "kind": "LIVE_SUBPKG",
        "path": "web3",
        "dispatch": "status",
    },
    "memory": {
        "module": "core.memory",
        "role": "Core memory package",
        "kind": "LIVE_SUBPKG",
        "path": "memory",
        "dispatch": "status",
    },
    "memory_store": {
        "module": "core.memory_store",
        "role": "Memory store adapters",
        "kind": "LIVE_SUBPKG",
        "path": "memory_store",
        "dispatch": "status",
    },
    "inference": {
        "module": "core.inference",
        "role": "Inference / chat pipeline",
        "kind": "LIVE_SUBPKG",
        "path": "inference",
        "dispatch": "status",
    },
    "training": {
        "module": "core.training",
        "role": "Training helpers",
        "kind": "LIVE_SUBPKG",
        "path": "training",
        "dispatch": "status",
    },
    "orchestration": {
        "module": "core.orchestration",
        "role": "SDK orch + shims to live v3/hive_router",
        "kind": "LIVE_SUBPKG",
        "path": "orchestration",
        "dispatch": "orchestration",
    },
    "api": {
        "module": "core.api",
        "role": "Core API helpers",
        "kind": "LIVE_SUBPKG",
        "path": "api",
        "dispatch": "status",
    },
    "config": {
        "module": "core.config",
        "role": "Core config",
        "kind": "LIVE_SUBPKG",
        "path": "config",
        "dispatch": "status",
    },
    "models": {
        "module": "core.models",
        "role": "Model helpers",
        "kind": "LIVE_SUBPKG",
        "path": "models",
        "dispatch": "status",
    },
    "identity": {
        "module": "core.identity",
        "role": "Persona / identity manager (gold)",
        "kind": "LIVE_MOD",
        "path": "identity.py",
        "dispatch": "identity",
    },
    "safety": {
        "module": "core.safety",
        "role": "Input/output safety filters (gold)",
        "kind": "LIVE_MOD",
        "path": "safety.py",
        "dispatch": "status",
    },
    "guardian": {
        "module": "core.guardian",
        "role": "Tool policy guardian",
        "kind": "LIVE_MOD",
        "path": "guardian.py",
        "dispatch": "guardian",
    },
    "deepen_cycle": {
        "module": "core.deepen_cycle",
        "role": "Deepen cycle engine",
        "kind": "LIVE_MOD",
        "path": "deepen_cycle.py",
        "dispatch": "status",
    },
    "self_improvement": {
        "module": "core.self_improvement",
        "role": "Training data / finetune orchestrator",
        "kind": "LIVE_MOD",
        "path": "self_improvement.py",
        "dispatch": "status",
    },
    "supervisor": {
        "module": "core.supervisor",
        "role": "Hierarchical supervisor agent",
        "kind": "LIVE_MOD",
        "path": "supervisor.py",
        "dispatch": "status",
    },
    "engine": {
        "module": "core.engine",
        "role": "Multi-tier memory engine",
        "kind": "LIVE_MOD",
        "path": "engine.py",
        "dispatch": "status",
    },
    "world_model": {
        "module": "core.world_model",
        "role": "World model",
        "kind": "LIVE_MOD",
        "path": "world_model.py",
        "dispatch": "status",
    },
    "plugins": {
        "module": "core.plugins",
        "role": "PluginSystem stub/core",
        "kind": "LIVE_MOD",
        "path": "plugins.py",
        "dispatch": "status",
    },
    "logging": {
        "module": "core.logging",
        "role": "Core logging helpers",
        "kind": "LIVE_SUBPKG",
        "path": "logging",
        "dispatch": "status",
    },
    "metrics": {
        "module": "core.metrics",
        "role": "Core metrics",
        "kind": "LIVE_SUBPKG",
        "path": "metrics",
        "dispatch": "status",
    },
    "tracing": {
        "module": "core.tracing",
        "role": "Tracing helpers",
        "kind": "LIVE_SUBPKG",
        "path": "tracing",
        "dispatch": "status",
    },
    # --- remaining root modules (ops + engines) ---
    "audit": {
        "module": "core.audit",
        "role": "Audit / compliance / observability",
        "kind": "LIVE_MOD",
        "path": "audit.py",
        "dispatch": "status",
    },
    "auto_model_detector": {
        "module": "core.auto_model_detector",
        "role": "Scan GGUF dirs and classify models",
        "kind": "LIVE_MOD",
        "path": "auto_model_detector.py",
        "dispatch": "status",
    },
    "bootstrap": {
        "module": "core.bootstrap",
        "role": "Core bootstrap helper",
        "kind": "LIVE_MOD",
        "path": "bootstrap.py",
        "dispatch": "status",
    },
    "closed_loop": {
        "module": "core.closed_loop",
        "role": "Local self-improvement closed loop",
        "kind": "LIVE_MOD",
        "path": "closed_loop.py",
        "dispatch": "status",
    },
    "core_extensions": {
        "module": "core.core_extensions",
        "role": "GGUF/LoRA manifest extensions",
        "kind": "LIVE_MOD",
        "path": "core_extensions.py",
        "dispatch": "status",
    },
    "critique": {
        "module": "core.critique",
        "role": "Self-critique engine",
        "kind": "LIVE_MOD",
        "path": "critique.py",
        "dispatch": "status",
    },
    "harden_repos": {
        "module": "core.harden_repos",
        "role": "Repo harden / policy apply",
        "kind": "OPS_UTIL",
        "path": "harden_repos.py",
        "dispatch": "status",
    },
    "local_models": {
        "module": "core.local_models",
        "role": "Local model manager (LLM/embed/image/audio)",
        "kind": "LIVE_MOD",
        "path": "local_models.py",
        "dispatch": "local_models",
    },
    "orchestrator_loop": {
        "module": "core.orchestrator",
        "role": "Thin evolve/memory/auto-train loop orchestrator",
        "kind": "LIVE_MOD",
        "path": "orchestrator.py",
        "dispatch": "status",
    },
    "provider": {
        "module": "core.provider",
        "role": "SelfHealingProvider + GGUF/PEFT helpers",
        "kind": "LIVE_MOD",
        "path": "provider.py",
        "dispatch": "status",
    },
    "promoter": {
        "module": "core.realai_promoter",
        "role": "Promote canonical modules into core",
        "kind": "OPS_UTIL",
        "path": "realai_promoter.py",
        "dispatch": "status",
    },
    "retirement": {
        "module": "core.realai_retirement",
        "role": "Flag obsolete unreferenced modules",
        "kind": "OPS_UTIL",
        "path": "realai_retirement.py",
        "dispatch": "status",
    },
    "root_flow": {
        "module": "core.realai_root_flow",
        "role": "Root architecture reconstruction walker",
        "kind": "OPS_UTIL",
        "path": "realai_root_flow.py",
        "dispatch": "status",
    },
    "root_walker": {
        "module": "core.realai_root_walker",
        "role": "Whole-repo nested walker / ability extract",
        "kind": "OPS_UTIL",
        "path": "realai_root_walker.py",
        "dispatch": "status",
    },
    "self_healing_core": {
        "module": "core.realai_self_healing_core",
        "role": "Self-healing core helpers",
        "kind": "LIVE_MOD",
        "path": "realai_self_healing_core.py",
        "dispatch": "status",
    },
    "visualizer": {
        "module": "core.realai_visualizer",
        "role": "ASCII architecture visualizer",
        "kind": "OPS_UTIL",
        "path": "realai_visualizer.py",
        "dispatch": "status",
    },
    "repo_engineer": {
        "module": "core.repo_engineer",
        "role": "Repo engineer helpers",
        "kind": "OPS_UTIL",
        "path": "repo_engineer.py",
        "dispatch": "status",
    },
    "repo_organizer": {
        "module": "core.repo_organizer",
        "role": "Organize mis-homed files into proper locations",
        "kind": "OPS_UTIL",
        "path": "repo_organizer.py",
        "dispatch": "status",
    },
    "rise_system": {
        "module": "core.rise_system",
        "role": "RISE recursive introspective self-improvement",
        "kind": "LIVE_MOD",
        "path": "rise_system.py",
        "dispatch": "status",
    },
    "runtime": {
        "module": "core.runtime",
        "role": "Runtime launcher stub",
        "kind": "LIVE_MOD",
        "path": "runtime.py",
        "dispatch": "status",
    },
    "self_builder": {
        "module": "core.self_builder",
        "role": "Local self-builder (GGUF + repo tools)",
        "kind": "LIVE_MOD",
        "path": "self_builder.py",
        "dispatch": "status",
    },
    "unified_orchestrator": {
        "module": "core.unified_orchestrator",
        "role": "Scan-manifest unified orch blueprint",
        "kind": "BLUEPRINT",
        "path": "unified_orchestrator.py",
        "dispatch": "status",
    },
}


def _resolve(name: str) -> Optional[str]:
    key = (name or "").strip().lower().replace("-", "_")
    if not key:
        return None
    if key in CORE_REGISTRY:
        return key
    for cid, meta in CORE_REGISTRY.items():
        if key == str(meta.get("path") or "").lower().replace(".py", "").replace("\\", "/").split("/")[-1]:
            return cid
        if key == str(meta.get("module") or "").rsplit(".", 1)[-1].lower():
            return cid
    return None


def _inventory() -> Dict[str, Any]:
    modules = []
    for cid, meta in CORE_REGISTRY.items():
        rel = str(meta.get("path") or "")
        path = _CORE / rel
        modules.append(
            {
                "id": cid,
                "role": meta.get("role"),
                "kind": meta.get("kind"),
                "module": meta.get("module"),
                "path": str(path),
                "present": path.exists(),
            }
        )
    # leftover root py not in registry
    known = {str(m.get("path")) for m in CORE_REGISTRY.values()}
    extras = []
    if _CORE.is_dir():
        for p in sorted(_CORE.iterdir()):
            if p.name == "__pycache__":
                continue
            if p.is_file() and p.name not in known and p.name not in {Path(k).name for k in known}:
                extras.append({"name": p.name, "bytes": p.stat().st_size, "kind": "file"})
            if p.is_dir() and p.name not in known:
                extras.append({"name": p.name, "kind": "dir"})
    return {
        "ok": True,
        "ability": "core_surface",
        "unified": True,
        "core_dir": str(_CORE),
        "import_as": "core (via PYTHONPATH …/realai)",
        "http_orch_gold": "realai.orchestration.v3_orchestrator",
        "modules": modules,
        "extras_unregistered": extras[:40],
        "note": (
            "core/orchestration/v3_orchestrator + hive_router are shims to live orch. "
            "Junk (add.py/arrayprint.py/package.json) quarantined under _quarantine/core_unify_20260830."
        ),
    }


def _run(cid: str, raw_input: str = "", ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ctx = dict(ctx or {})
    meta = CORE_REGISTRY[cid]
    out: Dict[str, Any] = {
        "ok": True,
        "core": cid,
        "module": meta.get("module"),
        "role": meta.get("role"),
    }
    dispatch = str(meta.get("dispatch") or "status")
    mod_name = str(meta.get("module"))

    try:
        mod = importlib.import_module(mod_name)
    except Exception as e:
        # Soft status: module is registered but may need optional deps
        path = _CORE / str(meta.get("path") or "")
        return {
            "ok": True,
            "core": cid,
            "module": mod_name,
            "role": meta.get("role"),
            "degraded": True,
            "import_error": str(e),
            "path": str(path),
            "present": path.exists(),
            "via": "degraded",
            "hint": "Registered in core_surface; install optional deps or fix imports to fully load",
            "trace": traceback.format_exc()[-400:],
        }

    if dispatch == "agents":
        try:
            from core.agents import get_agent_registry, list_tools

            out["result"] = {
                "agents": sorted(get_agent_registry().keys()),
                "tools": list_tools() if callable(list_tools) else None,
            }
            out["via"] = "core.agents"
        except Exception as e:
            out["result"] = {"exports": [n for n in dir(mod) if not n.startswith("_")][:40], "error": str(e)}
            out["via"] = mod_name
        return out

    if dispatch == "tools":
        try:
            from core.tools.registry import ToolRegistry

            # soft construct if possible
            out["result"] = {
                "exports": [n for n in dir(mod) if not n.startswith("_")][:40],
                "ToolRegistry": True,
            }
            try:
                from realai.orchestration.v3_runtime_bridge import tools_catalog

                # count core.* in orch catalog
                names = [
                    ((t.get("function") or {}).get("name") or "")
                    for t in tools_catalog()
                ]
                out["result"]["orch_core_tools"] = [n for n in names if n.startswith("core.")][:30]
            except Exception:
                pass
            out["via"] = "core.tools"
        except Exception as e:
            out["ok"] = False
            out["error"] = str(e)
        return out

    if dispatch == "security":
        out["result"] = {"exports": [n for n in dir(mod) if not n.startswith("_")][:40]}
        try:
            from core.security.python_sandbox import PythonSandbox

            out["result"]["PythonSandbox"] = True
        except Exception as e:
            out["result"]["sandbox_error"] = str(e)
        out["via"] = "core.security"
        return out

    if dispatch == "identity":
        try:
            from core.identity import IdentityManager

            out["result"] = {
                "IdentityManager": True,
                "exports": [n for n in dir(mod) if not n.startswith("_")][:40],
            }
            out["via"] = "core.identity"
        except Exception as e:
            out["ok"] = False
            out["error"] = str(e)
        return out

    if dispatch == "guardian":
        try:
            from core.guardian import guardian_mode, check_tool_call

            out["result"] = {
                "mode": guardian_mode() if callable(guardian_mode) else None,
                "check_tool_call": callable(check_tool_call),
            }
            out["via"] = "core.guardian"
        except Exception as e:
            out["result"] = {"exports": [n for n in dir(mod) if not n.startswith("_")][:40], "error": str(e)}
            out["via"] = mod_name
        return out

    if dispatch == "orchestration":
        out["result"] = {
            "exports": [n for n in dir(mod) if not n.startswith("_")][:40],
            "v3_shim": "realai.orchestration.v3_orchestrator",
            "hive_router_shim": "realai.orchestration.hive_router",
        }
        try:
            from core.orchestration.hive_router import register_routes

            out["result"]["routes"] = register_routes()
        except Exception as e:
            out["result"]["routes_error"] = str(e)
        out["via"] = "core.orchestration"
        return out

    if dispatch == "local_models":
        try:
            from core.local_models import LocalModelManager, LocalModelType

            mgr = LocalModelManager()
            out["result"] = {
                "LocalModelManager": True,
                "types": [t.value for t in LocalModelType],
                "models_dir": str(getattr(mgr, "models_dir", "")),
            }
            out["via"] = "core.local_models"
        except Exception as e:
            out["result"] = {
                "exports": [n for n in dir(mod) if not n.startswith("_")][:40],
                "error": str(e),
            }
            out["via"] = mod_name
        return out

    # generic status
    out["result"] = {"exports": [n for n in dir(mod) if not n.startswith("_")][:40]}
    out["via"] = mod_name
    return out


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or "list").lower().strip()
    name = str(ctx.get("core") or ctx.get("id") or ctx.get("name") or ctx.get("module") or "").strip()

    if action in {"list", "inventory", "status", "registry", "map", "unify_map", ""}:
        inv = _inventory()
        if name:
            cid = _resolve(name)
            if cid:
                inv["selected"] = next(m for m in inv["modules"] if m["id"] == cid)
            else:
                inv["selected_name"] = name
        return inv

    if action in {"run", "invoke", "dispatch"}:
        raw = str(input or "")
        cid = _resolve(name) if name else None
        if not cid and raw:
            parts = raw.split(None, 1)
            cid = _resolve(parts[0])
            raw = parts[1] if len(parts) > 1 else ""
        if not cid:
            return {
                "ok": False,
                "error": "core_id_required",
                "known": sorted(CORE_REGISTRY.keys()),
                "hint": "action=run core=agents|tools|security|voice|web3|identity|orchestration|…",
            }
        return _run(cid, raw_input=raw, ctx=ctx)

    return {
        "ok": False,
        "error": f"unknown_action:{action}",
        "actions": ["list", "run"],
        "known": sorted(CORE_REGISTRY.keys()),
    }
