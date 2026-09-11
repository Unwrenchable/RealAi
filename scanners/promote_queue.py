"""
Canonical promote_queue
=======================
Recovered from scanners/assemble_gold_index.py outputs
(scan_results/promote_queue.json) and scanners/promote_gold.py.

Static loader only. Does not promote files or walk disks on import.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

STATUS = "recovered"
CANONICAL_NAME = "promote_queue"
RECOVERED_FROM = "scanners/assemble_gold_index.py + scanners/promote_gold.py"

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT = _ROOT / "scan_results" / "promote_queue.json"


def queue_path() -> Path:
    return _DEFAULT


def load_promote_queue(path: Optional[Path] = None) -> Dict[str, Any]:
    target = path or _DEFAULT
    if not target.is_file():
        return {"status": "missing_artifact", "path": str(target), "items": []}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("status", "loaded")
            return data
        if isinstance(data, list):
            return {"status": "loaded", "items": data}
        return {"status": "loaded", "raw": data}
    except Exception as exc:
        return {"status": "unreadable", "error": str(exc), "path": str(target)}


def actionable_items(data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    payload = data if data is not None else load_promote_queue()
    items = payload.get("items") or payload.get("queue") or []
    if isinstance(payload.get("promote"), list) and not items:
        items = payload["promote"]
    out: List[Dict[str, Any]] = []
    if not isinstance(items, list):
        return out
    for item in items:
        if not isinstance(item, dict):
            continue
        action = str(item.get("action") or "")
        if action in {"promote", "needs_review", "rewrite"}:
            out.append(item)
    return out


def describe() -> Dict[str, Any]:
    loaded = load_promote_queue()
    return {
        "canonical": CANONICAL_NAME,
        "status": STATUS,
        "recovered_from": RECOVERED_FROM,
        "artifact": str(_DEFAULT),
        "artifact_status": loaded.get("status"),
        "actionable": len(actionable_items(loaded)),
    }
