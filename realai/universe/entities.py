"""Detect entities inside mapped worlds (agents, organs, top-level packages)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


def detect_entities(workspace: Path, worlds: List[Dict[str, Any]]) -> Dict[str, Any]:
    sample: List[Dict[str, str]] = []
    count = 0

    # Hive agents
    for base in (
        workspace / ".github" / "agents",
        workspace / "realai" / ".github" / "agents",
    ):
        if base.is_dir():
            for p in sorted(base.glob("*.json")):
                count += 1
                if len(sample) < 12:
                    sample.append({"type": "hive-agent", "id": p.stem, "path": str(p)})

    # Organs catalog if present
    organs = workspace / "realai" / "modules" / "organs" / "ORGANS_CATALOG.json"
    if organs.is_file():
        count += 1
        sample.append({"type": "organs-catalog", "id": "ORGANS_CATALOG", "path": str(organs)})

    # World roots themselves
    for w in worlds:
        count += 1
        if len(sample) < 20:
            sample.append({"type": "world", "id": w.get("id", ""), "path": str(w.get("path") or "")})

    return {"count": count, "sample": sample}