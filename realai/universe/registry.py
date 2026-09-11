"""Universal Registry — entities, environments, interactions across worlds."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from realai.universe.worlds import list_worlds, primary_workspace


def _hive_agents(workspace: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for base in (workspace / ".github" / "agents", workspace / "realai" / ".github" / "agents"):
        if not base.is_dir():
            continue
        for p in sorted(base.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8-sig"))
            except Exception:
                data = {"id": p.stem}
            out.append(
                {
                    "kind": "entity",
                    "type": "hive-agent",
                    "id": str(data.get("id") or p.stem),
                    "role": data.get("role"),
                    "path": str(p),
                    "world": "primary",
                }
            )
    seen = set()
    uniq = []
    for e in out:
        if e["id"] in seen:
            continue
        seen.add(e["id"])
        uniq.append(e)
    return uniq


def build_registry(workspace: Path | None = None) -> Dict[str, Any]:
    ws = primary_workspace(workspace)
    worlds = list_worlds(ws)
    entities = _hive_agents(ws)
    environments: List[Dict[str, Any]] = []
    for w in worlds:
        environments.append(
            {
                "kind": "environment",
                "id": w.get("id"),
                "name": w.get("name"),
                "path": w.get("path"),
                "world_kind": w.get("kind"),
            }
        )
    interactions: List[Dict[str, Any]] = []
    primary = next((w for w in worlds if w.get("kind") == "primary"), None)
    if primary:
        for w in worlds:
            if w is primary:
                continue
            interactions.append(
                {
                    "kind": "interaction",
                    "type": "cross-world-link",
                    "from": primary.get("id"),
                    "to": w.get("id"),
                    "channel": "knowledge-graph",
                }
            )
    organs = ws / "realai" / "modules" / "organs" / "ORGANS_CATALOG.json"
    if organs.is_file():
        entities.append(
            {
                "kind": "entity",
                "type": "organs-catalog",
                "id": "organs-catalog",
                "path": str(organs),
                "world": "primary",
            }
        )
    return {
        "ok": True,
        "name": "Universal Registry",
        "workspace": str(ws),
        "counts": {
            "entities": len(entities),
            "environments": len(environments),
            "interactions": len(interactions),
            "worlds": len(worlds),
        },
        "entities": entities,
        "environments": environments,
        "interactions": interactions,
    }