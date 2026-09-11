"""
Canonical archive_triage
========================
Recovered implementation: scanners/recover_archive_gold.py
Artifact name from Jul 24 map: scan_results/dds3_archive_triage.json
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

STATUS = "recovered_alias"
CANONICAL_NAME = "archive_triage"
RECOVERED_FROM = "scanners/recover_archive_gold.py"

_ROOT = Path(__file__).resolve().parents[1]
_JSON = _ROOT / "scan_results" / "dds3_archive_triage.json"

try:
    from recover_archive_gold import copy_file, sha  # noqa: F401
except Exception:
    try:
        from .recover_archive_gold import copy_file, sha  # type: ignore  # noqa: F401
    except Exception:
        pass


def load_triage(path: Optional[Path] = None) -> Dict[str, Any]:
    target = path or _JSON
    if not target.is_file():
        return {"status": "missing_artifact", "path": str(target)}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        return {"status": "loaded", "data": data}
    except Exception as exc:
        return {"status": "unreadable", "error": str(exc)}


def describe() -> Dict[str, Any]:
    return {
        "canonical": CANONICAL_NAME,
        "status": STATUS,
        "recovered_from": RECOVERED_FROM,
        "artifact": load_triage().get("status"),
    }
