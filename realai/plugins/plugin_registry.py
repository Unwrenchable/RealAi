"""Plugin Registry rewritten 2026-08-30 for RealAI static reconstruction.

Manages the RealAI plugin/ability registry stored in:
    realai/abilities/registry.json

This module provides:
    - load_registry()
    - save_registry()
    - list_plugins()
    - register_plugin()
    - remove_plugin()
    - resolve_plugin()

No plugin code is executed; this is purely structural.
plugins/registry.json is treated as a fallback husk (array of plugin dicts).
No original plugin_registry.py body was recovered from any scanned tree.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_PKG = Path(__file__).resolve().parents[1]
REGISTRY_PATH = _PKG / "abilities" / "registry.json"
_HUSK_PATH = _PKG / "plugins" / "registry.json"


def _empty() -> Dict[str, Any]:
    return {"plugins": {}, "abilities": [], "tools": [], "tasks": []}


def _as_plugins_map(data: Any) -> Dict[str, Any]:
    """Normalize live shapes into a name -> meta map. Never imports modules."""
    out: Dict[str, Any] = {}
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                name = item.get("name") or item.get("id")
                if name:
                    out[str(name)] = item
        return out
    if not isinstance(data, dict):
        return out
    plugins = data.get("plugins")
    if isinstance(plugins, dict):
        for name, meta in plugins.items():
            if isinstance(meta, dict):
                out[str(name)] = meta
            else:
                out[str(name)] = {"name": name, "value": meta}
    elif isinstance(plugins, list):
        for item in plugins:
            if isinstance(item, dict):
                name = item.get("name") or item.get("id")
                if name:
                    out[str(name)] = item
    abilities = data.get("abilities")
    if isinstance(abilities, list):
        for item in abilities:
            if isinstance(item, dict):
                name = item.get("name") or item.get("id")
                if name and str(name) not in out:
                    out[str(name)] = item
    return out


def load_registry() -> Dict[str, Any]:
    path = REGISTRY_PATH if REGISTRY_PATH.is_file() else _HUSK_PATH
    if not path.is_file():
        return _empty()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _empty()
    plugins = _as_plugins_map(raw)
    if isinstance(raw, dict):
        return {
            "plugins": plugins,
            "abilities": raw.get("abilities", []),
            "tools": raw.get("tools", []),
            "tasks": raw.get("tasks", []),
            "path": str(path),
        }
    return {
        "plugins": plugins,
        "abilities": [],
        "tools": [],
        "tasks": [],
        "path": str(path),
    }


def save_registry(registry: Dict[str, Any]) -> None:
    """Write abilities-shaped JSON. Does not execute plugin code."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "abilities": registry.get("abilities", []),
        "tools": registry.get("tools", []),
        "tasks": registry.get("tasks", []),
    }
    plugins = registry.get("plugins") or {}
    if plugins and not payload["abilities"]:
        payload["abilities"] = list(plugins.values()) if isinstance(plugins, dict) else list(plugins)
    REGISTRY_PATH.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def list_plugins() -> List[str]:
    registry = load_registry()
    return list(registry.get("plugins", {}).keys())


def register_plugin(name: str, meta: Dict[str, Any]) -> bool:
    registry = load_registry()
    plugins = registry.setdefault("plugins", {})
    if name in plugins:
        return False
    entry = {
        "name": name,
        "description": meta.get("description", ""),
        "version": meta.get("version", "1.0"),
        "entrypoint": meta.get("entrypoint", None),
        "enabled": meta.get("enabled", True),
        "type": meta.get("type", "plugin"),
        "capabilities": meta.get("capabilities", []),
    }
    plugins[name] = entry
    abilities = registry.setdefault("abilities", [])
    if isinstance(abilities, list):
        abilities.append(entry)
    save_registry(registry)
    return True


def remove_plugin(name: str) -> bool:
    registry = load_registry()
    plugins = registry.get("plugins", {})
    if name not in plugins:
        return False
    del plugins[name]
    abilities = registry.get("abilities")
    if isinstance(abilities, list):
        registry["abilities"] = [
            item for item in abilities
            if not (isinstance(item, dict) and (item.get("name") == name or item.get("id") == name))
        ]
    save_registry(registry)
    return True


def resolve_plugin(name: str) -> Optional[Dict[str, Any]]:
    """Return plugin/ability metadata only. Never imports or executes it."""
    registry = load_registry()
    return registry.get("plugins", {}).get(name)