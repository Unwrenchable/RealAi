"""
Canonical verify_matrix
=======================
Jul 24 Drive map listed:
  C:\\realai\\scanners\\verify_v3_matrix.py
  C:\\realai\\scan_results\\phase4_verify_matrix.json
  C:\\realai\\scan_results\\phase4_verify_matrix.md

The .py body was not present on any recovered GitHub branch.
Static loader for the artifact name only.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

STATUS = "unresolved"
CANONICAL_NAME = "verify_matrix"
RECOVERED_FROM = None
REASON = "verify_v3_matrix.py existed on C:\\realai\\scanners (Jul 24 map) but source was not in GitHub recovery branches."

_ROOT = Path(__file__).resolve().parents[1]
_JSON = _ROOT / "scan_results" / "phase4_verify_matrix.json"


def load_matrix(path: Optional[Path] = None) -> Dict[str, Any]:
    target = path or _JSON
    if not target.is_file():
        return {"status": "missing_artifact", "path": str(target), "reason": REASON}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        return {"status": "loaded_artifact_only", "data": data}
    except Exception as exc:
        return {"status": "unreadable", "error": str(exc)}


def describe() -> Dict[str, Any]:
    return {
        "canonical": CANONICAL_NAME,
        "status": STATUS,
        "reason": REASON,
        "artifact": load_matrix().get("status"),
    }
