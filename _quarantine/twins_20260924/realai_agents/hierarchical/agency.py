"""Agency specialist helpers for hierarchical / Hive use.

Loads persona markdown from ``agents/agency/`` and registry rows from
``agents/agentx/agents.json`` (tags include ``agency``).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[2]  # C:\RealAI-clean
_AGENCY = _ROOT / "agents" / "agency"
_REGISTRY = _ROOT / "agents" / "agentx" / "agents.json"


@lru_cache(maxsize=1)
def _registry_rows() -> List[Dict[str, Any]]:
    if not _REGISTRY.is_file():
        return []
    try:
        data = json.loads(_REGISTRY.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return [r for r in data if isinstance(r, dict) and r.get("id")]


def list_agency_agents() -> List[Dict[str, Any]]:
    """Return registry rows tagged agency / agency-agents."""
    out = []
    for row in _registry_rows():
        tags = [str(t).lower() for t in (row.get("tags") or [])]
        if "agency" in tags or "agency-agents" in tags or row.get("division"):
            out.append(row)
    return out


def list_agency_divisions() -> List[str]:
    divs = sorted(
        {
            str(r.get("division") or "").strip()
            for r in list_agency_agents()
            if r.get("division")
        }
        | {p.name for p in _AGENCY.iterdir() if p.is_dir()}
    )
    return [d for d in divs if d]


def _resolve_persona_path(agent_id: str) -> Optional[Path]:
    aid = (agent_id or "").strip().lower()
    if not aid:
        return None
    for row in list_agency_agents():
        if str(row.get("id") or "").lower() != aid:
            continue
        rel = row.get("source_path")
        if rel:
            cand = _AGENCY / str(rel)
            if cand.is_file():
                return cand
    # fallback: search by stem
    hits = list(_AGENCY.rglob(f"*{aid}*.md"))
    return hits[0] if hits else None


def load_agency_persona(agent_id: str) -> Optional[str]:
    """Return full markdown persona text for an Agency specialist."""
    path = _resolve_persona_path(agent_id)
    if not path:
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def get_agency_specialist(agent_id: str) -> Optional[Dict[str, Any]]:
    """Registry row + persona prompt for hierarchical / Console use."""
    aid = (agent_id or "").strip().lower()
    row = next((r for r in list_agency_agents() if str(r.get("id") or "").lower() == aid), None)
    if not row:
        return None
    persona = load_agency_persona(aid)
    return {
        "id": row.get("id"),
        "role": row.get("role"),
        "description": row.get("description"),
        "tags": row.get("tags") or [],
        "division": row.get("division"),
        "source_path": row.get("source_path"),
        "system_prompt": persona or row.get("description") or row.get("role"),
        "preferred_profile": row.get("preferred_profile") or "balanced",
        "required_tools": row.get("required_tools") or [],
    }


# Division → hierarchical specialist type (for Supervisor routing hints)
DIVISION_TO_SPECIALIST = {
    "engineering": "coder",
    "design": "creative",
    "marketing": "creative",
    "sales": "executor",
    "product": "researcher",
    "project-management": "executor",
    "testing": "critic",
    "support": "executor",
    "finance": "researcher",
    "academic": "researcher",
    "specialized": "executor",
    "game-development": "creative",
    "paid-media": "creative",
    "spatial-computing": "coder",
}


def map_division_to_specialist(division: str) -> str:
    return DIVISION_TO_SPECIALIST.get((division or "").lower(), "researcher")
