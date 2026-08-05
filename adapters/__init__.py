"""Adapter registry bootstrap for recovered snapshots.

Each entry maps a recovered snapshot id to its on-disk path so the living
system can discover unique code without linear-merging histories.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "registry" / "modules.yaml"


def load_modules() -> list[dict[str, Any]]:
    if yaml is None:
        return []
    if not REGISTRY_PATH.exists():
        return []
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    return list(data.get("modules") or [])


def resolve_path(module_id: str) -> Path | None:
    for m in load_modules():
        if m.get("id") == module_id:
            p = ROOT / str(m.get("path", ""))
            return p if p.exists() else None
    return None


def list_capabilities() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for m in load_modules():
        out[str(m.get("id"))] = list(m.get("capabilities") or [])
    return out
