"""Canonical era_map. Recovered from assemble_gold_index.py::era_of. Static only."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
STATUS = "recovered"
CANONICAL_NAME = "era_map"
RECOVERED_FROM = "scanners/assemble_gold_index.py::era_of"
ERA_LABELS = ("og_mess", "archive", "backup", "duplicate", "recovered", "clean", "models", "training", "other")
def norm_path(p: str) -> str:
    return p.replace("\\", "/").lstrip("./")
def era_of(rel: str) -> str:
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
    if r.startswith(("realai/", "apps/", "core/", "agents/")):
        return "clean"
    if r.startswith("models/"):
        return "models"
    if r.startswith("training/"):
        return "training"
    if r.startswith("_quarantine/") or "/_quarantine/" in r:
        return "quarantine"
    return "other"
def load_era_map(path: Optional[Path] = None) -> Dict[str, Any]:
    target = path or (Path(__file__).resolve().parents[1] / "scan_results" / "era_map.json")
    if not target.is_file():
        return {"status": "missing_artifact", "path": str(target), "eras": {}}
    import json
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"status": "loaded", "raw": data}
    except Exception as exc:
        return {"status": "unreadable", "error": str(exc), "path": str(target)}
def classify_many(paths: Iterable[str]) -> Dict[str, str]:
    return {p: era_of(p) for p in paths}
