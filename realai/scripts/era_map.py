"""
Canonical era_map
=================
Recovered from scanners/assemble_gold_index.py::era_of
and referenced by realai/ability_catalog.py.

Static only: classifies a relative path into an era label.
Does not walk disks, start scans, or write scan_results on import.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

STATUS = "recovered"
CANONICAL_NAME = "era_map"
RECOVERED_FROM = "scanners/assemble_gold_index.py::era_of"

ERA_LABELS = (
    "og_mess",
    "archive",
    "backup",
    "duplicate",
    "recovered",
    "clean",
    "models",
    "training",
    "other",
)

# Roots registered by recovered scan_desktop_missing_gold.py / ability_catalog.py
REGISTERED_ROOTS = [
    r"C:\RealAI-clean",
    r"C:\realai",
    r"C:\realai\realai-clean",
    r"C:\Users\tsmit\realai-clean",
    r"C:\Users\tsmit\projects\realai-clean",
    r"C:\Users\tsmit\realai_historical_backups",
    r"C:\Users\tsmit\backups",
    r"C:\RealAI_Recovery_SAFE",
    r"C:\realai_grok_export",
]


def norm_path(p: str) -> str:
    return p.replace("\\", "/").lstrip("./")


def era_of(rel: str) -> str:
    """Classify a relative path into an era. Recovered logic."""
    r = norm_path(rel).lower()
    if r.startswith("realai_og_mess") or "/realai_og_mess/" in r:
        return "og_mess"
    if r.startswith("archive/") or "/archive/" in r:
        return "archive"
    if ".backup" in r or "historical_backup" in r:
        return "backup"
    if "__dup" in r or " copy" in r:
        return "duplicate"
    if r.startswith("recovered/"):
        return "recovered"
    if r.startswith("realai/") or r.startswith("apps/") or r.startswith("core/") or r.startswith("agents/"):
        return "clean"
    if r.startswith("models/"):
        return "models"
    if r.startswith("training/"):
        return "training"
    if r.startswith("_quarantine/") or "/_quarantine/" in r:
        return "quarantine"
    return "other"


def load_era_map(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load scan_results/era_map.json if present. Never scans the repo."""
    target = path or (Path(__file__).resolve().parents[1] / "scan_results" / "era_map.json")
    if not target.is_file():
        return {"status": "missing_artifact", "path": str(target), "eras": {}}
    try:
        import json
        data = json.loads(target.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        return {"status": "loaded", "raw": data}
    except Exception as exc:
        return {"status": "unreadable", "error": str(exc), "path": str(target)}


def classify_many(paths: Iterable[str]) -> Dict[str, str]:
    return {p: era_of(p) for p in paths}


def describe() -> Dict[str, Any]:
    return {
        "canonical": CANONICAL_NAME,
        "status": STATUS,
        "recovered_from": RECOVERED_FROM,
        "labels": list(ERA_LABELS),
        "registered_roots": list(REGISTERED_ROOTS),
    }
