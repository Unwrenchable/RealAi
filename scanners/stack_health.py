"""Canonical stack_health

RECONSTRUCTED 2026-08-30. No original body was recovered.
Static path-presence only. Does not import RealAI runtime, start
servers, dispatch, or train.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

STATUS = "reconstructed_static"
CANONICAL_NAME = "stack_health"
RECOVERED_FROM = None

_HERE = Path(__file__).resolve().parent
if _HERE.name == "scanners" and _HERE.parent.name == "realai":
    _PKG = _HERE.parent
    _ROOT = _PKG.parent
else:
    _ROOT = _HERE.parent
    _PKG = _ROOT / "realai"

EXPECTED = [
    "realai/__init__.py",
    "realai/world_model.py",
    "realai/world_model.json",
    "realai/local_models.py",
    "realai/memory/engine.py",
    "realai/plugins/plugin_registry.py",
    "realai/scanners/assemble_gold_index.py",
    "realai/scanners/promote_gold.py",
    "realai/scanners/dds3_missing_files.py",
    "realai/scanners/ingest_realai_roots.py",
    "benchmarks/base.py",
    "benchmarks/runner.py",
    "benchmarks/bench_world_model.py",
    "benchmarks/bench_stack_health.py",
    "scan_results/era_map.json",
    "agents",
    "abilities",
]


def check() -> Dict[str, Any]:
    missing: List[str] = []
    present: List[str] = []
    for rel in EXPECTED:
        p = _ROOT / rel
        if not p.exists():
            alt = _PKG / Path(rel).name if rel.startswith("realai/") else None
            if alt is not None and alt.exists():
                present.append(rel)
                continue
            missing.append(rel)
        else:
            present.append(rel)
    return {
        "canonical": CANONICAL_NAME,
        "status": STATUS,
        "present": present,
        "missing": missing,
        "healthy": not missing,
        "executed_runtime": False,
        "root": str(_ROOT),
        "pkg": str(_PKG),
    }


def describe() -> Dict[str, Any]:
    return check()