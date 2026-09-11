"""
Canonical dds3_missing_files
============================
Jul 24 Drive map listed C:\\realai\\scanners\\dds3_missing_files.py
Gold index promote target: realai/memory/dds3_missing_files.py

Source body was not present on recovered GitHub branches
(unification/ultimate-all scanners only had dds3_deep_gold_map.py).
"""
from __future__ import annotations

from typing import Any, Dict

STATUS = "unresolved"
CANONICAL_NAME = "dds3_missing_files"
RECOVERED_FROM = None
REASON = "Listed in Jul 24 file map and gold_index.md promote queue; .py body not in GitHub recovery snapshots."


def describe() -> Dict[str, Any]:
    return {
        "canonical": CANONICAL_NAME,
        "status": STATUS,
        "reason": REASON,
        "related_recovered": "scanners/dds3_deep_gold_map.py",
    }
