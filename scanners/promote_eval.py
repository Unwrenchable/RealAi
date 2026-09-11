"""Canonical filename: promote_eval.py

RECONSTRUCTED 2026-08-30. No original body in any tree.
Related: scanners/promote_gold.py (do not run; it writes promote artifacts).

Static describe-only module. Does not promote files or walk disks.
"""
from __future__ import annotations

from typing import Any, Dict

STATUS = "reconstructed_static"
CANONICAL_NAME = "promote_eval"
RECOVERED_FROM = None
RELATED = "scanners/promote_gold.py"


def describe() -> Dict[str, Any]:
    return {
        "canonical": CANONICAL_NAME,
        "status": STATUS,
        "related": RELATED,
        "note": "Use promote_gold.py as the recovered implementation; this name is a static eval surface only.",
        "writes": False,
        "executed_runtime": False,
    }


def available() -> bool:
    return False
