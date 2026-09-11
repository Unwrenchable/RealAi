"""Unified surface for ``realai/orchestration`` — live gold package.

One HTTP product: ``v3_orchestrator`` on :8001.
SDK pieces (agent/orchestrator/pipeline/memory/tools) stay in-process libraries.
Legacy/scan/unified-blueprint are dispatched, not second servers.
Nests under ``realai/orchestrators/`` are handled by ``ability.nest_orchestrators``.
"""

from __future__ import annotations

import importlib
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

ABILITY = {
    "id": "orchestration_surface",
    "name": "orchestration_surface",
    "type": "ability",
    "status": "LIVE",
    "source": "realai/orchestration/*",
    "dest": "abilities/orchestration_surface.py",
    "capabilities": [
        "v3",
        "hive_router",
        "runtime_bridge",
        "sdk_orchestrator",
        "pipeline",
        "memory",
        "tools",
        "tts",
        "legacy_scan",
        "nests",
    ],
    "secrets_policy": "none",
}

_ROOT = Path(__file__).resolve().parents[1]
_PKG = _ROOT / "realai" / "orchestration"

# Canonical module ids inside the live orchestration package.
ORCH_REGISTRY: Dict[str, Dict[str, Any]] = {
    "v3": {
        "module": "realai.orchestration.v3_orchestrator",
        "file": "v3_orchestrator.py",
        "role": "Live HTTP product (:8001) — UI → Vulkan",
        "kind": "LIVE_SERVER",
        "do_not_start_extra_server": True,
        "aliases": ["v3_orchestrator", "live", "product", "http"],
    },
    "bridge": {
        "module": "realai.orchestration.v3_runtime_bridge",
        "file": "v3_runtime_bridge.py",
        "role": "Tools catalog, multi-agent, ability execute, workspace/craft bridge",
        "kind": "LIVE_LIB",
        "aliases": ["v3_runtime_bridge", "runtime_bridge"],
    },
    "hive_router": {
        "module": "realai.orchestration.hive_router",
        "file": "hive_router.py",
        "role": "Hive routes + run_cycle (planner→specialist→critic→executor)",
        "kind": "LIVE_LIB",
        "aliases": ["hive", "router"],
    },
    "sdk_agent": {
        "module": "realai.orchestration.agent",
        "file": "agent.py",
        "role": "BaseAgent SDK primitive",
        "kind": "SDK",
        "aliases": ["agent", "base_agent"],
    },
    "sdk_orchestrator": {
        "module": "realai.orchestration.orchestrator",
        "file": "orchestrator.py",
        "role": "Multi-agent Orchestrator pool (sequential/parallel/auto-route)",
        "kind": "SDK",
        "aliases": ["orchestrator", "pool"],
    },
    "sdk_pipeline": {
        "module": "realai.orchestration.pipeline",
        "file": "pipeline.py",
        "role": "Fixed-sequence Pipeline over BaseAgents",
        "kind": "SDK",
        "aliases": ["pipeline"],
    },
    "sdk_memory": {
        "module": "realai.orchestration.memory",
        "file": "memory.py",
        "role": "SharedMemory for multi-agent workflows",
        "kind": "SDK",
        "aliases": ["memory", "shared_memory"],
    },
    "sdk_tools": {
        "module": "realai.orchestration.tools",
        "file": "tools.py",
        "role": "Tool / ToolRegistry for agents",
        "kind": "SDK",
        "aliases": ["tools", "tool_registry"],
    },
    "tts": {
        "module": "realai.orchestration.tts_routing",
        "file": "tts_routing.py",
        "role": "Voice-aware reply routing (speak vs text)",
        "kind": "LIVE_LIB",
        "aliases": ["tts_routing", "voice"],
    },
    "nests": {
        "module": "abilities.nest_orchestrators",
        "file": "nest_orchestrators.py",
        "role": "Unified nest dispatcher (realai/orchestrators/* abilities)",
        "kind": "LIVE_ABILITY",
        "aliases": ["nest_orchestrators", "nest"],
    },
    "entry_shim": {
        "module": "realai.orchestration.realai_orchestrator",
        "file": "realai_orchestrator.py",
        "role": "Launcher shim → v3 (realai_orchestrator name)",
        "kind": "SHIM",
        "aliases": ["realai_orchestrator"],
        "do_not_start_extra_server": True,
    },
    "legacy_scan": {
        "module": "realai.orchestration.legacy_orchestrator",
        "file": "legacy_orchestrator.py",
        "role": "Manifest scan/patch-target engine (legacy)",
        "kind": "LEGACY",
        "aliases": ["legacy", "scan_patch", "legacy_orchestrator"],
    },
    "unified_blueprint": {
        "module": "realai.orchestration.unified_orchestrator",
        "file": "unified_orchestrator.py",
        "role": "Scan-manifest blueprint aggregator (not a server)",
        "kind": "BLUEPRINT",
        "aliases": ["unified", "unified_orchestrator", "blueprint"],
    },
    "package_init": {
        "module": "realai.orchestration",
        "file": "__init__.py",
        "role": "Package exports (voice + optional BaseAgent/Pipeline)",
        "kind": "PACKAGE",
        "aliases": ["init", "__init__"],
    },
}


def _resolve(name: str) -> Optional[str]:
    key = (name or "").strip().lower().replace("-", "_")
    if not key:
        return None
    if key in ORCH_REGISTRY:
        return key
    for oid, meta in ORCH_REGISTRY.items():
        if key == str(meta.get("file") or "").lower().replace(".py", ""):
            return oid
        if key in [str(a).lower() for a in (meta.get("aliases") or [])]:
            return oid
        if key == str(meta.get("module") or "").rsplit(".", 1)[-1].lower():
            return oid
    return None


def _inventory() -> Dict[str, Any]:
    modules = []
    for oid, meta in ORCH_REGISTRY.items():
        path = _PKG / str(meta.get("file") or "")
        # nests ability lives under abilities/
        if oid == "nests":
            path = _ROOT / "abilities" / "nest_orchestrators.py"
        modules.append(
            {
                "id": oid,
                "role": meta.get("role"),
                "kind": meta.get("kind"),
                "module": meta.get("module"),
                "file": meta.get("file"),
                "present": path.is_file(),
                "bytes": path.stat().st_size if path.is_file() else 0,
                "aliases": meta.get("aliases") or [],
                "do_not_start_extra_server": bool(meta.get("do_not_start_extra_server")),
            }
        )
    # related singular paths (not inside package, but often confused)
    related = {
        "realai.orchestrator.py": {
            "path": str(_ROOT / "realai" / "orchestrator.py"),
            "exists": (_ROOT / "realai" / "orchestrator.py").is_file(),
            "note": "shim → realai.plugins.orchestrator (scan engine), NOT the HTTP hive",
        },
        "realai.orchestrator/": {
            "path": str(_ROOT / "realai" / "orchestrator"),
            "exists": (_ROOT / "realai" / "orchestrator").is_dir(),
            "note": "TS run.ts helper dir — not Python hive",
        },
        "realai.orchestrators/": {
            "path": str(_ROOT / "realai" / "orchestrators"),
            "exists": (_ROOT / "realai" / "orchestrators").is_dir(),
            "note": "nest salvage pile — use ability.nest_orchestrators",
        },
        "realai.v3_orchestrator": {
            "path": str(_ROOT / "realai" / "v3_orchestrator.py"),
            "exists": (_ROOT / "realai" / "v3_orchestrator.py").is_file(),
            "note": "package-root shim → realai.orchestration.v3_orchestrator",
        },
    }
    return {
        "ok": True,
        "ability": "orchestration_surface",
        "unified": True,
        "live_product": "realai.orchestration.v3_orchestrator",
        "package_dir": str(_PKG),
        "modules": modules,
        "related_paths": related,
        "note": (
            "Unify rule: one :8001 process. SDK modules are libraries. "
            "Nests dispatch via ability.nest_orchestrators. "
            "Do not run legacy/nested v3 copies as servers."
        ),
    }


def _run_module(oid: str, raw_input: str = "", ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ctx = dict(ctx or {})
    meta = ORCH_REGISTRY[oid]
    out: Dict[str, Any] = {
        "ok": True,
        "orch": oid,
        "kind": meta.get("kind"),
        "module": meta.get("module"),
        "role": meta.get("role"),
    }

    if meta.get("do_not_start_extra_server") or oid in ("v3", "entry_shim"):
        try:
            from realai.v3_runtime_bridge import orch_health, vulkan_health

            out["live"] = {
                "orch": orch_health(),
                "vulkan": vulkan_health(),
                "hint": "Product already on :8001 — chat/tools/hive/craft",
            }
            out["via"] = meta.get("module")
        except Exception as e:
            out["live"] = {"error": str(e)}
            out["via"] = meta.get("module")
        return out

    if oid == "bridge":
        from realai.orchestration import v3_runtime_bridge as br

        out["result"] = {
            "tools_count": len(br.tools_catalog()),
            "hive_agents": br.hive_agents_status(),
            "exports": [n for n in dir(br) if not n.startswith("_")][:40],
        }
        out["via"] = "realai.orchestration.v3_runtime_bridge"
        return out

    if oid == "hive_router":
        from realai.orchestration import hive_router as hr

        action = str(ctx.get("action") or "routes").lower()
        if action in ("cycle", "run"):
            task = raw_input or str(ctx.get("task") or "orchestration status")
            out["result"] = hr.run_cycle(
                task,
                agent=str(ctx.get("agent") or "researcher"),
                persist=bool(ctx.get("persist", True)),
            )
            out["via"] = "hive_router.run_cycle"
        else:
            out["result"] = hr.register_routes()
            out["via"] = "hive_router.register_routes"
        return out

    if oid == "nests":
        from abilities.nest_orchestrators import run as nest_run

        action = str(ctx.get("nest_action") or ctx.get("action") or "list")
        nest = str(ctx.get("nest") or "")
        out["result"] = nest_run(
            input=raw_input,
            context={"action": action, "nest": nest, **{k: v for k, v in ctx.items() if k not in ("action",)}},
        )
        out["via"] = "ability.nest_orchestrators"
        return out

    if oid == "tts":
        from realai.orchestration.tts_routing import hive_voice_entry, route_reply, should_speak

        text = raw_input or str(ctx.get("text") or "RealAI voice check")
        intent = str(ctx.get("intent") or "chat")
        out["result"] = {
            "should_speak": should_speak(intent, text),
            "route": route_reply(text, intent),
            "hive_voice_entry": hive_voice_entry(),
        }
        out["via"] = "tts_routing"
        return out

    if oid.startswith("sdk_"):
        mod = importlib.import_module(str(meta["module"]))
        exports = [n for n in dir(mod) if not n.startswith("_")]
        # light status without requiring a live client
        detail: Dict[str, Any] = {"exports": exports[:40]}
        if oid == "sdk_orchestrator" and hasattr(mod, "Orchestrator"):
            detail["class"] = "Orchestrator"
            detail["hint"] = "Use with BaseAgent + SharedMemory; or live multi_agent_run"
            try:
                from realai.v3_runtime_bridge import run_multi_agent

                detail["live_multi_agent"] = run_multi_agent(
                    raw_input or str(ctx.get("task") or "sdk orchestrator status"),
                    mode=str(ctx.get("mode") or "pipeline"),
                )
            except Exception as e:
                detail["live_multi_agent_error"] = str(e)
        if oid == "sdk_memory" and hasattr(mod, "SharedMemory"):
            mem = mod.SharedMemory()
            key, val = "orchestration_surface", {"ok": True, "probe": raw_input or "ping"}
            if hasattr(mem, "store"):
                mem.store(key, val)
                detail["probe"] = mem.retrieve(key) if hasattr(mem, "retrieve") else val
            elif hasattr(mem, "set"):
                mem.set(key, val)
                detail["probe"] = mem.get(key) if hasattr(mem, "get") else val
            else:
                detail["methods"] = [n for n in dir(mem) if not n.startswith("_")][:20]
                detail["probe"] = "SharedMemory loaded"
        if oid == "sdk_tools" and hasattr(mod, "ToolRegistry"):
            detail["class"] = "ToolRegistry"
        if oid == "sdk_pipeline" and hasattr(mod, "Pipeline"):
            detail["class"] = "Pipeline"
        if oid == "sdk_agent" and hasattr(mod, "BaseAgent"):
            detail["class"] = "BaseAgent"
        out["result"] = detail
        out["via"] = meta["module"]
        return out

    if oid == "legacy_scan":
        import os

        manifest = _ROOT / "realai" / "manifest.json"
        mod = importlib.import_module("realai.orchestration.legacy_orchestrator")
        if not manifest.is_file():
            out["result"] = {
                "ok": True,
                "skipped_full_scan": True,
                "class": "RealAIOrchestrator",
                "methods": [n for n in dir(mod.RealAIOrchestrator) if n.startswith("phase_")][:20],
                "hint": "realai/manifest.json missing",
            }
            out["via"] = "legacy_orchestrator (introspect)"
            return out
        prev = os.getcwd()
        try:
            os.chdir(str(_ROOT))
            orch = mod.RealAIOrchestrator()
            active = orch.phase_scan()
        finally:
            os.chdir(prev)
        out["result"] = {
            "ok": True,
            "active_keys": list(active.keys())[:40] if isinstance(active, dict) else type(active).__name__,
        }
        out["via"] = "legacy_orchestrator.phase_scan"
        return out

    if oid == "unified_blueprint":
        mod = importlib.import_module("realai.orchestration.unified_orchestrator")
        # look for a scan manifest; otherwise return blueprint class info
        candidates = [
            _ROOT / "scan_results" / "unify_manifest.json",
            _ROOT / "scan_results" / "weights_gold_map.json",
            _ROOT / "realai" / "scan_results" / "unify_manifest.json",
        ]
        manifest = next((p for p in candidates if p.is_file()), None)
        if manifest is None:
            out["result"] = {
                "ok": True,
                "class": "UnifiedOrchestrator",
                "hint": "No unify scan manifest found — blueprint only",
                "looked_for": [str(p) for p in candidates],
            }
            out["via"] = "unified_orchestrator (introspect)"
            return out
        uo = mod.UnifiedOrchestrator(_ROOT, manifest)
        out["result"] = uo.build()
        out["via"] = f"unified_orchestrator.build:{manifest.name}"
        return out

    if oid == "package_init":
        mod = importlib.import_module("realai.orchestration")
        out["result"] = {"exports": [n for n in dir(mod) if not n.startswith("_")][:40]}
        out["via"] = "realai.orchestration"
        return out

    out["ok"] = False
    out["error"] = f"no_runner:{oid}"
    return out


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or "list").lower().strip()
    name = str(ctx.get("orch") or ctx.get("id") or ctx.get("name") or ctx.get("module") or "").strip()

    if action in {"list", "inventory", "status", "registry", "map", "unify_map", ""}:
        inv = _inventory()
        if name:
            oid = _resolve(name)
            if not oid:
                inv["ok"] = False
                inv["error"] = f"unknown_orch_module:{name}"
                inv["known"] = sorted(ORCH_REGISTRY.keys())
                return inv
            inv["selected"] = next(m for m in inv["modules"] if m["id"] == oid)
        return inv

    if action in {"run", "invoke", "dispatch", "cycle"}:
        raw = str(input or "")
        oid = _resolve(name) if name else None
        if not oid and raw:
            parts = raw.split(None, 1)
            maybe = _resolve(parts[0])
            if maybe:
                oid = maybe
                raw = parts[1] if len(parts) > 1 else ""
        if action == "cycle" and not oid:
            oid = "hive_router"
            ctx.setdefault("action", "cycle")
        if not oid:
            return {
                "ok": False,
                "error": "orch_id_required",
                "known": sorted(ORCH_REGISTRY.keys()),
                "hint": "action=run orch=v3|bridge|hive_router|sdk_orchestrator|nests|tts|legacy_scan|…",
            }
        # when cycling hive_router, force cycle action
        if action == "cycle":
            ctx["action"] = "cycle"
        return _run_module(oid, raw_input=raw, ctx=ctx)

    return {
        "ok": False,
        "error": f"unknown_action:{action}",
        "actions": ["list", "run", "cycle", "unify_map"],
        "known": sorted(ORCH_REGISTRY.keys()),
    }
