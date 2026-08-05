"""Adapter registry bootstrap for recovered snapshots + promoted core modules + organs hive."""
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


def living_stack() -> dict[str, Any]:
    """Status of promoted living modules (not ghosted)."""
    from adapters.training import training_status
    from adapters.memory import get_memory_stack
    from adapters.agents import agents_status
    from adapters.organs import organs_status
    try:
        from adapters.self_improvement import self_improvement_status
        si = self_improvement_status()
    except Exception as e:
        si = {"error": str(e)}
    try:
        from adapters.rackup_coach import rackup_coach_status
        rc = rackup_coach_status()
    except Exception as e:
        rc = {"error": str(e)}
    return {
        "provider": "realai",
        "provider_kind": "local-first OpenAI-compatible full provider (not a wrapper)",
        "training": training_status(),
        "memory": get_memory_stack(),
        "agents": agents_status(),
        "organs_hive": organs_status(),
        "self_improvement": si,
        "rackup_coach": rc,
        "promoted_unique": {
            "ability_catalog": (ROOT / "realai" / "ability_catalog.py").exists(),
            "agent_protocol": (ROOT / "realai" / "agent_protocol.py").exists(),
            "aura_memory": (ROOT / "realai" / "aura_memory.py").exists(),
            "hierarchical_agent": (ROOT / "core" / "agents" / "hierarchical_agent.py").exists(),
            "desktop_unique": (ROOT / "modules" / "desktop_unique").exists(),
            "agents_advanced": (ROOT / "modules" / "agents_advanced").exists(),
            "rackup_coach": (ROOT / "plugins" / "rackup_coach").exists(),
        },
    }
