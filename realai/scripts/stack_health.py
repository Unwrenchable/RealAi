"""
Canonical stack_health
======================
No recovered stack_health.py body was found.

This module performs STATIC presence checks only (path existence).
It does not import RealAI runtime, start servers, or run benchmarks.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

STATUS = "reconstructed_static"
CANONICAL_NAME = "stack_health"
RECOVERED_FROM = None
REASON = "No stack_health.py in GitHub recovery branches or Jul 24 file map."

_ROOT = Path(__file__).resolve().parents[1]

EXPECTED = [
    "realai/__init__.py",
    "realai/memory/engine.py",
    "realai/world_model.py",
    "realai/ability_catalog.py",
    "realai/tools.py",
    "benchmarks/base.py",
    "benchmarks/runner.py",
    "scanners/assemble_gold_index.py",
    "scanners/promote_gold.py",
    "scanners/dds3_deep_gold_map.py",
    "core/__init__.py",
    "agents",
    "providers",
    "packages",
    "training/__init__.py",
    "models/__init__.py",
]


def check() -> Dict[str, Any]:
    missing: List[str] = []
    present: List[str] = []
    for rel in EXPECTED:
        p = _ROOT / rel
        if p.exists():
            present.append(rel)
        else:
            missing.append(rel)
    return {
        "canonical": CANONICAL_NAME,
        "status": STATUS,
        "present": present,
        "missing": missing,
        "healthy": not missing,
        "executed_runtime": False,
    }


def describe() -> Dict[str, Any]:
    return check()
