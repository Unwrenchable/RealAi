"""Universe Mode on/off and full status payload."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from realai.universe.architect import survey as architect_survey
from realai.universe.creative_engine import status as creative_status
from realai.universe.dispatcher import status as dispatcher_status
from realai.universe.doctor import diagnose
from realai.universe.entities import detect_entities
from realai.universe.hardening import status as hardening_status
from realai.universe.hierarchy import describe as hierarchy_describe
from realai.universe.knowledge_graph import build_graph
from realai.universe.memory_bridge import memory_status
from realai.universe.pattern_engine import status as pattern_status
from realai.universe.recipe_engine import status as recipe_status
from realai.universe.registry import build_registry
from realai.universe.worlds import list_worlds, primary_workspace


def is_universe_on() -> bool:
    raw = (os.environ.get("REALAI_UNIVERSE") or "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    try:
        multi = int(os.environ.get("REALAI_MULTI_WS") or "0")
    except ValueError:
        multi = 0
    return multi >= 2


def universe_status(workspace: Path | None = None) -> Dict[str, Any]:
    ws = primary_workspace(workspace)
    on = is_universe_on()
    worlds = list_worlds(ws)
    entities = detect_entities(ws, worlds)
    mem = memory_status(ws)
    reg = build_registry(ws)
    graph = build_graph(ws)
    doc = diagnose(ws)
    arch = architect_survey(ws)
    return {
        "ok": True,
        "universe": "ON" if on else "OFF",
        "universe_on": on,
        "workspace": str(ws),
        "worlds": len(worlds),
        "world_list": worlds,
        "entities": "detected" if entities.get("count", 0) > 0 else "none",
        "entity_count": entities.get("count", 0),
        "entity_sample": entities.get("sample") or [],
        "memory": mem.get("label") or ("active" if mem.get("active") else "inactive"),
        "memory_detail": mem,
        "hierarchy": hierarchy_describe(),
        "subsystems": {
            "registry": {"ok": True, "counts": reg.get("counts")},
            "knowledge_graph": {"ok": True, "nodes": graph.get("node_count"), "edges": graph.get("edge_count")},
            "pattern_engine": pattern_status(),
            "recipe_engine": recipe_status(),
            "hardening": hardening_status(),
            "creative_engine": creative_status(),
            "universal_doctor": {"ok": doc.get("ok"), "failed": doc.get("failed")},
            "universal_architect": {"ok": True, "worlds": len(arch.get("worlds") or [])},
            "universal_dispatcher": dispatcher_status(),
        },
        "env": {
            "REALAI_UNIVERSE": os.environ.get("REALAI_UNIVERSE"),
            "REALAI_MULTI_WS": os.environ.get("REALAI_MULTI_WS"),
            "REALAI_MEMORY": os.environ.get("REALAI_MEMORY"),
        },
        "note": "Highest-level orchestration surface. Cross-world engines are present scaffolds, not live mutation loops.",
    }