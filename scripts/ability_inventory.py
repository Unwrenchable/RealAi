"""
Canonical ability_inventory
===========================
Recovered from realai/ability_catalog.py (Phase 5F) and the
scan_results/dds3_ability_inventory.json artifact name in the Jul 24 map.

Static: re-exports the recovered catalog. Does not scan disks on import.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

STATUS = "recovered"
CANONICAL_NAME = "ability_inventory"
RECOVERED_FROM = "realai/ability_catalog.py"

_ROOT = Path(__file__).resolve().parents[1]
_JSON = _ROOT / "scan_results" / "dds3_ability_inventory.json"

try:
    from realai.ability_catalog import RUNDOWN_ABILITIES, _STATUS_WEIGHT  # type: ignore
except Exception:
    RUNDOWN_ABILITIES: List[Dict[str, Any]] = []
    _STATUS_WEIGHT = {}


def load_inventory_json(path: Optional[Path] = None) -> Dict[str, Any]:
    target = path or _JSON
    if not target.is_file():
        return {"status": "missing_artifact", "path": str(target), "items": list(RUNDOWN_ABILITIES)}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        return {"status": "loaded", "items": data}
    except Exception as exc:
        return {"status": "unreadable", "error": str(exc), "items": list(RUNDOWN_ABILITIES)}


def abilities() -> List[Dict[str, Any]]:
    payload = load_inventory_json()
    items = payload.get("items") or payload.get("abilities") or RUNDOWN_ABILITIES
    return list(items) if isinstance(items, list) else list(RUNDOWN_ABILITIES)


def describe() -> Dict[str, Any]:
    return {
        "canonical": CANONICAL_NAME,
        "status": STATUS,
        "recovered_from": RECOVERED_FROM,
        "catalog_count": len(RUNDOWN_ABILITIES),
        "weights": dict(_STATUS_WEIGHT),
    }
