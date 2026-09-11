"""Canonical filename: plugin_registry.py

RECONSTRUCTED 2026-08-30 as a wrap of scripts/plugin_registry_builder.py.
No plugin_registry.py existed. This module loads realai/plugins/registry.json
if present. It does NOT run find_plugins() / disk hunts / writes.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

STATUS = "reconstructed_wrap"
CANONICAL_NAME = "plugin_registry"
RECOVERED_FROM = "scripts/plugin_registry_builder.py"

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT = _ROOT / "realai" / "plugins" / "registry.json"


def load_registry(path: Optional[Path] = None) -> Dict[str, Any]:
    target = path or _DEFAULT
    if not target.is_file():
        return {"status": "missing_artifact", "path": str(target), "plugins": []}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "unreadable", "error": str(exc), "path": str(target), "plugins": []}
    if isinstance(data, list):
        return {"status": "loaded", "plugins": data}
    if isinstance(data, dict):
        plugins = data.get("plugins") or data.get("abilities") or []
        return {"status": "loaded", "plugins": plugins, "raw_keys": list(data.keys())}
    return {"status": "unexpected_shape", "plugins": []}


def list_plugins() -> List[Any]:
    return list(load_registry().get("plugins") or [])


def describe() -> Dict[str, Any]:
    loaded = load_registry()
    return {
        "canonical": CANONICAL_NAME,
        "status": STATUS,
        "recovered_from": RECOVERED_FROM,
        "artifact_status": loaded.get("status"),
        "plugin_count": len(loaded.get("plugins") or []),
        "writes": False,
        "scans": False,
    }
