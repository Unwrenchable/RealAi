"""Universal Architect — structural view of the universe map."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from realai.universe.hierarchy import describe as hierarchy_describe
from realai.universe.worlds import list_worlds, primary_workspace


def survey(workspace: Path | None = None) -> Dict[str, Any]:
    ws = primary_workspace(workspace)
    worlds = list_worlds(ws)
    layout: List[Dict[str, Any]] = []
    for name in ("realai", "agents", "apps", "packages", "scripts", "training", "providers"):
        p = ws / name
        layout.append({"name": name, "exists": p.is_dir(), "path": str(p)})
    return {
        "ok": True,
        "name": "Universal Architect",
        "workspace": str(ws),
        "hierarchy": hierarchy_describe(),
        "worlds": worlds,
        "layout": layout,
        "note": "Structural survey only. Does not reorganize trees.",
    }