"""Canonical filename: ability_matrix.py

RECONSTRUCTED 2026-08-30. No original body in any tree.
Related: realai/abilities/registry.json and scanners/ability_inventory.py.

Static loader for ability registry JSON. Does not scan or execute abilities.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

STATUS = "reconstructed_static"
CANONICAL_NAME = "ability_matrix"
RECOVERED_FROM = "realai/abilities/registry.json"

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT = _ROOT / "realai" / "abilities" / "registry.json"


def load_matrix(path: Optional[Path] = None) -> Dict[str, Any]:
    target = path or _DEFAULT
    if not target.is_file():
        return {"status": "missing_artifact", "path": str(target)}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        return {"status": "loaded_artifact_only", "data": data}
    except Exception as exc:
        return {"status": "unreadable", "error": str(exc), "path": str(target)}


def describe() -> Dict[str, Any]:
    loaded = load_matrix()
    abilities = []
    data = loaded.get("data") or {}
    if isinstance(data, dict):
        abilities = data.get("abilities") or []
    return {
        "canonical": CANONICAL_NAME,
        "status": STATUS,
        "artifact_status": loaded.get("status"),
        "ability_count": len(abilities) if isinstance(abilities, list) else 0,
        "executed_runtime": False,
    }
