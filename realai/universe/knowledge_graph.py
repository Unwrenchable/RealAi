"""Cross-world knowledge graph — static adjacency between mapped worlds."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from realai.universe.worlds import list_worlds, primary_workspace


def build_graph(workspace: Path | None = None) -> Dict[str, Any]:
    ws = primary_workspace(workspace)
    worlds = list_worlds(ws)
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    for w in worlds:
        nodes.append(
            {
                "id": w.get("id"),
                "label": w.get("name"),
                "path": w.get("path"),
                "kind": w.get("kind"),
            }
        )
    ids = [n["id"] for n in nodes]
    if ids:
        root = ids[0]
        for nid in ids[1:]:
            edges.append({"from": root, "to": nid, "rel": "learns-with"})
            edges.append({"from": nid, "to": root, "rel": "reports-to"})
        for i, a in enumerate(ids[1:], start=1):
            for b in ids[i + 1 :]:
                edges.append({"from": a, "to": b, "rel": "peer-pattern"})
    return {
        "ok": True,
        "name": "Cross-World Knowledge Graph",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
        "note": "Static map from REALAI_WORKSPACE + EXTRA_WORKSPACES/REPO_PATHS. No training loop.",
    }