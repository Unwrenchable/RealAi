"""Unified RealAI plugins surface — live product vs salvage vs junk.

``realai/plugins`` mixed gold plugins with recovery nests and recycle-bin
site-packages noise. This ability inventories, dispatches LIVE plugins, and
can quarantine junk/numbered dups without touching salvage until promoted.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ABILITY = {
    "id": "plugins_surface",
    "name": "plugins_surface",
    "type": "ability",
    "status": "LIVE",
    "source": "realai/plugins/*",
    "dest": "abilities/plugins_surface.py",
    "capabilities": [
        "plugins",
        "rackup_coach",
        "atomic_fizz",
        "marketplace",
        "quarantine",
        "inventory",
        "unify",
    ],
    "secrets_policy": "none",
}

_ROOT = Path(__file__).resolve().parents[1]
_PLUGINS = _ROOT / "realai" / "plugins"
_PLUGINS_ROOT = _ROOT / "plugins"  # twin dump at repo root
_QUARANTINE = _ROOT / "_quarantine" / "plugins_unify_20260830"
_SCAN = _ROOT / "scan_results"


def _plugins_dir(ctx: Optional[Dict[str, Any]] = None) -> Path:
    raw = str((ctx or {}).get("plugins_root") or "").strip().lower()
    if raw in {"root", "repo", "top", str(_PLUGINS_ROOT).lower()}:
        return _PLUGINS_ROOT
    return _PLUGINS

# Live product plugins (dirs / modules we intentionally keep on the path).
LIVE_PLUGINS: Dict[str, Dict[str, Any]] = {
    "rackup_coach": {
        "path": "rackup_coach",
        "role": "RackUp coach / rating / SOTD / money audit",
        "kind": "LIVE_DIR",
        "aliases": ["rackup-coach"],
        "dispatch": "rackup",
    },
    "atomicfizz_coach": {
        "path": "atomicfizz_coach",
        "role": "Atomic Fizz / Caps coach stub (health, caps_context, wrist_ui_hint)",
        "kind": "LIVE_DIR",
        "aliases": ["atomicfizz-coach", "atomicfizz"],
        "dispatch": "atomicfizz",
    },
    "atomic_fizz_realai": {
        "path": "atomic_fizz_realai",
        "role": "Atomic Fizz NPC/quest/overseer/world gold",
        "kind": "LIVE_DIR",
        "aliases": [],
        "dispatch": "atomic_fizz",
    },
    "agent_tools": {
        "path": "agent_tools",
        "role": "agent_tools package bridge under plugins",
        "kind": "LIVE_DIR",
        "dispatch": "status",
    },
    "tools": {
        "path": "tools",
        "role": "Plugin tools catalog (device_selector, etc.)",
        "kind": "LIVE_DIR",
        "dispatch": "tools",
    },
    "plugin_marketplace": {
        "path": "plugin_marketplace.py",
        "role": "Plugin discovery / marketplace",
        "kind": "LIVE_PY",
        "aliases": ["plugin_plugin_marketplace"],
        "dispatch": "marketplace",
    },
    "plugin_registry": {
        "path": "plugin_registry.py",
        "role": "Structural plugin/ability registry (no exec)",
        "kind": "LIVE_PY",
        "dispatch": "registry",
    },
    "device_selector": {
        "path": "device_selector.py",
        "role": "Prefer cuda/directml/cpu",
        "kind": "LIVE_PY",
        "dispatch": "device",
    },
    "desktop_plugins": {
        "path": "desktop_plugins",
        "role": "Desktop lambda / UI plugin surface",
        "kind": "LIVE_DIR",
        "dispatch": "status",
    },
    "abilities": {
        "path": "abilities",
        "role": "Nested abilities mirror under plugins (prefer repo abilities/)",
        "kind": "LIVE_DIR",
        "dispatch": "status",
    },
}


def _classify_name(name: str, is_dir: bool) -> str:
    nl = name.lower()
    if nl in {"__pycache__", ".git"}:
        return "CACHE"
    if nl.startswith("c__realai_recovered_from_recycle_bin") or "site-packages" in nl:
        return "JUNK_SITEPACKAGES"
    # Third-party plugin stubs accidentally dropped at plugins root
    if nl in {
        "_loader.py",
        "_schema_validator.py",
        "_hypothesis_plugin.py",
        "mypy_plugin.py",
        "pytest_plugin.py",
    } or nl.startswith("c__realai_.venv"):
        return "JUNK_SITEPACKAGES"
    if re.match(r"plugin___init___\d+\.py$", nl):
        return "NUMBERED_DUP"
    if re.match(r"plugin_.+_\d+\.py$", nl) or re.match(r"realai-ish_.+_\d+\.py$", nl):
        return "NUMBERED_DUP"
    salvage_tokens = (
        "from-wsl",
        "from-zips",
        "from-accident",
        "from_aura",
        "recovery",
        "quarantine",
        "nested",
        "grok_export",
        "grok-realai",
        "clean-base",
        "local-",
        "tree_",
        "recycle",
        "dup1",
        "copy_plugins",
        "cotton-mistake",
        "homepc",
        "plugin-system",
        "plugin-boards",
        "agents-skills",
        "atomicfizzcaps-fork",
        "modules-runtime",
        "unique-modules",
        "feature-ui-desktop",
        "integration-hive",
        "real-fin_",
        "realai_sdk",
        "realai_recovery",
        "c_realai_plugins",
    )
    if any(t in nl for t in salvage_tokens):
        return "SALVAGE_NEST"
    if name in LIVE_PLUGINS or any(name == a for m in LIVE_PLUGINS.values() for a in (m.get("aliases") or [])):
        return "LIVE"
    if nl in {"plugins", "py", "core", "benchmarks", "scripts", "related", "memory_ecosystem"}:
        return "SUPPORT"
    if nl.startswith("c__realai"):
        return "SALVAGE_NEST"
    if is_dir:
        return "OTHER_DIR"
    if nl.endswith((".json", ".yaml", ".yml")):
        return "CONFIG"
    if nl.endswith(".py"):
        return "ROOT_PY"
    return "OTHER"


def _sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def _inventory(deep_files: bool = False, plugins_dir: Optional[Path] = None) -> Dict[str, Any]:
    dirs_out: List[Dict[str, Any]] = []
    files_out: List[Dict[str, Any]] = []
    cats = Counter()
    plugins = plugins_dir or _PLUGINS

    if not plugins.is_dir():
        return {"ok": False, "error": f"missing_plugins_dir:{plugins}"}

    for p in sorted(plugins.iterdir(), key=lambda x: x.name.lower()):
        if p.name == "__pycache__":
            continue
        cat = _classify_name(p.name, p.is_dir())
        # eslint/node_modules dumps at root plugins
        nl = p.name.lower()
        if nl.startswith("c__realai_apps_frontend_node_modules") or nl in {
            "eslint",
            "eslint.cmd",
            "eslint.ps1",
            "tsc",
            "tsc.cmd",
            "tsc.ps1",
            "tsserver",
            "tsserver.cmd",
            "tsserver.ps1",
            "resolve",
            "resolve.cmd",
            "resolve.ps1",
            "semver",
            "semver.cmd",
            "semver.ps1",
        }:
            cat = "JUNK_SITEPACKAGES"
        cats[cat] += 1
        item = {
            "name": p.name,
            "kind": "dir" if p.is_dir() else "file",
            "category": cat,
            "bytes": p.stat().st_size if p.is_file() else None,
        }
        if p.is_dir():
            try:
                item["child_files"] = sum(1 for _ in p.rglob("*") if _.is_file())
            except Exception:
                item["child_files"] = None
            dirs_out.append(item)
        else:
            if deep_files or cat in {"JUNK_SITEPACKAGES", "NUMBERED_DUP", "LIVE", "CONFIG", "SALVAGE_NEST"} or p.suffix in {".py", ".json", ".yaml"}:
                files_out.append(item)

    live = []
    for lid, meta in LIVE_PLUGINS.items():
        path = plugins / str(meta["path"])
        # prefer realai/plugins for live presence truth
        live_path = _PLUGINS / str(meta["path"])
        live.append(
            {
                "id": lid,
                "role": meta.get("role"),
                "kind": meta.get("kind"),
                "path": str(live_path),
                "present": live_path.exists(),
                "aliases": meta.get("aliases") or [],
            }
        )

    return {
        "ok": True,
        "ability": "plugins_surface",
        "unified": True,
        "plugins_dir": str(plugins),
        "quarantine_dir": str(_QUARANTINE),
        "counts": {
            "top_dirs": len(dirs_out),
            "top_files": sum(1 for p in plugins.iterdir() if p.is_file()),
            "by_category": dict(cats),
        },
        "live_plugins": live,
        "dirs": dirs_out,
        "files_sample": files_out[:300],
        "note": (
            "LIVE plugins stay under realai/plugins. JUNK + NUMBERED_DUP quarantine. "
            "apply_salvage also moves SALVAGE_NEST dirs/files. Root plugins/ is a twin dump."
        ),
    }


def _resolve_live(name: str) -> Optional[str]:
    key = (name or "").strip().lower().replace("-", "_")
    if not key:
        return None
    if key in LIVE_PLUGINS:
        return key
    for lid, meta in LIVE_PLUGINS.items():
        aliases = [str(a).lower().replace("-", "_") for a in (meta.get("aliases") or [])]
        path = str(meta.get("path") or "").lower().replace("-", "_").replace(".py", "")
        if key in aliases or key == path or key == lid.replace("-", "_"):
            return lid
    return None


def _run_live(lid: str, raw_input: str = "", ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ctx = dict(ctx or {})
    meta = LIVE_PLUGINS[lid]
    dispatch = str(meta.get("dispatch") or "status")
    out: Dict[str, Any] = {"ok": True, "plugin": lid, "role": meta.get("role"), "dispatch": dispatch}

    if dispatch == "rackup":
        ability = str(ctx.get("ability") or "").strip() or "coach"
        if ability.lower() in {"status", "rackup_coach", "rackup"}:
            ability = "coach"
        from realai.v3_runtime_bridge import execute_registry_tool

        name = ability if ability.startswith("ability.") else f"ability.{ability}"
        out["result"] = execute_registry_tool(name, {"input": raw_input, "context": ctx})
        out["via"] = name
        return out

    if dispatch == "atomicfizz":
        # Stub plugin path — not atomic_fizz_realai JS engines.
        from plugins.atomicfizz_coach import invoke as atomicfizz_invoke

        ability = str(ctx.get("ability") or raw_input or "health").strip() or "health"
        if ability.lower() in {"status", "atomicfizz_coach", "atomicfizz", "atomicfizz-coach"}:
            ability = "health"
        player = ctx.get("player") if isinstance(ctx.get("player"), dict) else {}
        payload = ctx.get("payload") if isinstance(ctx.get("payload"), dict) else {}
        out["result"] = atomicfizz_invoke(ability, player, payload)
        out["via"] = "plugins.atomicfizz_coach.invoke"
        return out

    if dispatch == "atomic_fizz":
        # Prefer overseer / omnibrain / world_brain abilities
        target = str(ctx.get("ability") or raw_input or "overseer").strip() or "overseer"
        from realai.v3_runtime_bridge import execute_registry_tool

        aid = target if target.startswith("ability.") else f"ability.{target}"
        out["result"] = execute_registry_tool(aid, {"input": raw_input, "context": ctx})
        out["via"] = aid
        return out

    if dispatch == "marketplace":
        try:
            from realai.plugins import plugin_marketplace as pm

            exports = [n for n in dir(pm) if not n.startswith("_")]
            out["result"] = {"ok": True, "exports": exports[:40], "module": "realai.plugins.plugin_marketplace"}
            out["via"] = "plugin_marketplace"
        except Exception as e:
            out["ok"] = False
            out["error"] = str(e)
        return out

    if dispatch == "registry":
        try:
            from realai.plugins.plugin_registry import load_registry, list_plugins

            reg = load_registry()
            plugins = list_plugins() if callable(list_plugins) else reg.get("plugins")
            out["result"] = {
                "ok": True,
                "plugin_count": len(plugins) if isinstance(plugins, dict) else len(plugins or []),
                "registry_keys": list(reg.keys()) if isinstance(reg, dict) else [],
            }
            out["via"] = "plugin_registry"
        except Exception as e:
            # fallback husk
            husk = _PLUGINS / "registry.json"
            data = json.loads(husk.read_text(encoding="utf-8")) if husk.is_file() else []
            out["result"] = {"ok": True, "husk": data, "error": str(e)}
            out["via"] = "plugins/registry.json"
        return out

    if dispatch == "device":
        try:
            from realai.plugins.device_selector import get_device_name

            out["result"] = {"ok": True, "device": get_device_name()}
        except Exception as e:
            try:
                from realai.plugins.tools.device_selector import get_device_name

                out["result"] = {"ok": True, "device": get_device_name()}
            except Exception as e2:
                out["ok"] = False
                out["error"] = f"{e}; {e2}"
        out["via"] = "device_selector"
        return out

    if dispatch == "tools":
        tools_dir = _PLUGINS / "tools"
        names = sorted(p.stem for p in tools_dir.glob("*.py") if p.name != "__init__.py") if tools_dir.is_dir() else []
        out["result"] = {"ok": True, "tools": names[:80], "count": len(names)}
        out["via"] = "plugins/tools"
        return out

    # status default
    path = _PLUGINS / str(meta["path"])
    out["result"] = {
        "ok": True,
        "path": str(path),
        "exists": path.exists(),
        "kind": "dir" if path.is_dir() else "file",
    }
    out["via"] = "status"
    return out


def _quarantine_plan(plugins_dir: Optional[Path] = None) -> Dict[str, Any]:
    plugins = plugins_dir or _PLUGINS
    inv = _inventory(deep_files=True, plugins_dir=plugins)
    move_files: List[str] = []
    salvage_files: List[str] = []
    move_dirs: List[str] = []
    for f in inv.get("files_sample") or []:
        if f.get("category") in {"JUNK_SITEPACKAGES", "NUMBERED_DUP"}:
            move_files.append(f["name"])
        if f.get("category") == "SALVAGE_NEST":
            salvage_files.append(f["name"])
    # also scan all top files for those cats (files_sample may truncate)
    for p in plugins.iterdir():
        if not p.is_file():
            continue
        # reclassify with root-plugins junk heuristics via inventory categories
        cat = next((x["category"] for x in (inv.get("files_sample") or []) if x["name"] == p.name), None)
        if cat is None:
            cat = _classify_name(p.name, False)
            nl = p.name.lower()
            if nl.startswith("c__realai_apps_frontend_node_modules") or nl.startswith("c__realai_"):
                cat = "SALVAGE_NEST" if "site-packages" not in nl else "JUNK_SITEPACKAGES"
            if nl in {
                "eslint",
                "eslint.cmd",
                "eslint.ps1",
                "tsc",
                "tsc.cmd",
                "tsc.ps1",
                "tsserver",
                "tsserver.cmd",
                "tsserver.ps1",
                "resolve",
                "resolve.cmd",
                "resolve.ps1",
                "semver",
                "semver.cmd",
                "semver.ps1",
                "_loader.py",
                "_schema_validator.py",
                "_hypothesis_plugin.py",
                "mypy_plugin.py",
                "pytest_plugin.py",
            }:
                cat = "JUNK_SITEPACKAGES"
        if cat in {"JUNK_SITEPACKAGES", "NUMBERED_DUP"} and p.name not in move_files:
            move_files.append(p.name)
        if cat == "SALVAGE_NEST" and p.name not in salvage_files:
            salvage_files.append(p.name)
    for d in inv.get("dirs") or []:
        if d.get("category") == "SALVAGE_NEST":
            move_dirs.append(d["name"])
    return {
        "ok": True,
        "plugins_dir": str(plugins),
        "quarantine_dir": str(_QUARANTINE),
        "auto_move_files": sorted(set(move_files)),
        "auto_move_file_count": len(set(move_files)),
        "salvage_files_listed_not_moved": sorted(set(salvage_files)),
        "salvage_file_count": len(set(salvage_files)),
        "salvage_dirs_listed_not_moved": sorted(set(move_dirs)),
        "salvage_dir_count": len(set(move_dirs)),
        "rule": (
            "Default apply moves JUNK_SITEPACKAGES + NUMBERED_DUP files only. "
            "apply_salvage=true also moves SALVAGE_NEST dirs and path-mangled salvage files."
        ),
    }


def _apply_quarantine(
    *,
    apply_salvage: bool = False,
    dry_run: bool = True,
    plugins_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    plugins = plugins_dir or _PLUGINS
    plan = _quarantine_plan(plugins)
    moved: List[Dict[str, str]] = []
    errors: List[Dict[str, str]] = []

    targets: List[Tuple[Path, str]] = []
    for name in plan["auto_move_files"]:
        # prefer junk bucket; numbered dups separate
        cat = "JUNK_SITEPACKAGES"
        if name.lower().startswith("plugin_") and any(ch.isdigit() for ch in name):
            cat = "NUMBERED_DUP"
        dest_sub = "junk_sitepackages" if cat == "JUNK_SITEPACKAGES" else "numbered_dups"
        # root plugins twin goes under root_plugins/ subfolder
        if plugins == _PLUGINS_ROOT:
            dest_sub = f"root_plugins/{dest_sub}"
        targets.append((plugins / name, dest_sub))
    if apply_salvage:
        for name in plan.get("salvage_files_listed_not_moved") or []:
            sub = "salvage_nests" if plugins != _PLUGINS_ROOT else "root_plugins/salvage_nests"
            targets.append((plugins / name, sub))
        for name in plan.get("salvage_dirs_listed_not_moved") or []:
            sub = "salvage_nests" if plugins != _PLUGINS_ROOT else "root_plugins/salvage_nests"
            targets.append((plugins / name, sub))

    if not dry_run:
        _QUARANTINE.mkdir(parents=True, exist_ok=True)

    for src, sub in targets:
        if not src.exists():
            continue
        dest_dir = _QUARANTINE / sub
        dest = dest_dir / src.name
        entry = {"src": str(src), "dest": str(dest), "sub": sub}
        if dry_run:
            moved.append({**entry, "status": "dry_run"})
            continue
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                # collision: hash suffix
                dest = dest_dir / f"{src.stem}__{_sha1(src) if src.is_file() else 'dir'}{src.suffix}"
            shutil.move(str(src), str(dest))
            moved.append({**entry, "dest": str(dest), "status": "moved"})
        except Exception as e:
            errors.append({"src": str(src), "error": str(e)})

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "apply_salvage": apply_salvage,
        "moved_count": len([m for m in moved if m.get("status") == "moved"]),
        "planned_count": len(moved),
        "errors": errors,
        "moved": moved[:500],
    }
    _SCAN.mkdir(parents=True, exist_ok=True)
    man_path = _SCAN / "plugins_unify_quarantine.json"
    if not dry_run:
        man_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        # also keep plan snapshot
        (_SCAN / "plugins_unify_inventory.json").write_text(
            json.dumps(_inventory(deep_files=False), indent=2, default=str),
            encoding="utf-8",
        )
    else:
        (_SCAN / "plugins_unify_quarantine_dry_run.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

    return {
        "ok": True,
        "dry_run": dry_run,
        "manifest": str(man_path if not dry_run else _SCAN / "plugins_unify_quarantine_dry_run.json"),
        "planned_or_moved": len(moved),
        "errors": errors,
        "sample": moved[:20],
        "quarantine_dir": str(_QUARANTINE),
    }


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or "list").lower().strip()
    name = str(ctx.get("plugin") or ctx.get("id") or ctx.get("name") or "").strip()
    plugins = _plugins_dir(ctx)

    if action in {"list", "inventory", "status", "registry", "map", "unify_map", ""}:
        inv = _inventory(deep_files=bool(ctx.get("deep")), plugins_dir=plugins)
        if name:
            lid = _resolve_live(name)
            if lid:
                inv["selected"] = next(p for p in inv["live_plugins"] if p["id"] == lid)
            else:
                inv["selected_name"] = name
                inv["selected_category"] = _classify_name(name, (plugins / name).is_dir())
        return inv

    if action in {"run", "invoke", "dispatch"}:
        lid = _resolve_live(name or (input.split()[0] if input else ""))
        raw = input
        if not lid and input:
            parts = input.split(None, 1)
            lid = _resolve_live(parts[0])
            raw = parts[1] if len(parts) > 1 else ""
        if not lid:
            return {
                "ok": False,
                "error": "live_plugin_id_required",
                "known": sorted(LIVE_PLUGINS.keys()),
                "hint": "action=run plugin=rackup_coach|atomicfizz_coach|atomic_fizz_realai|plugin_marketplace|device_selector|tools",
            }
        return _run_live(lid, raw_input=raw, ctx=ctx)

    if action in {"quarantine_plan", "plan"}:
        return _quarantine_plan(plugins)

    if action in {"quarantine", "organize"}:
        return _apply_quarantine(
            apply_salvage=bool(ctx.get("apply_salvage")),
            dry_run=bool(ctx.get("dry_run") if ctx.get("dry_run") is not None else True),
            plugins_dir=plugins,
        )

    return {
        "ok": False,
        "error": f"unknown_action:{action}",
        "actions": ["list", "run", "quarantine_plan", "quarantine"],
        "known_live": sorted(LIVE_PLUGINS.keys()),
    }
