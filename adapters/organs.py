"""Organs / hive adapter — discover and call all 44 synthetic organs."""
from __future__ import annotations
from typing import Any


def organs_status() -> dict[str, Any]:
    from modules.organs import hive_status
    return hive_status()


def list_all_organs() -> list[dict[str, Any]]:
    from modules.organs import list_organs
    return list_organs()


def invoke_organ(organ_id: str, goal: str = "", payload: dict | None = None) -> dict[str, Any]:
    from modules.organs import call_organ
    r = call_organ(organ_id, goal=goal, payload=payload)
    return {
        "organ_id": r.organ_id,
        "ok": r.ok,
        "output": r.output,
        "notes": r.notes,
        "metrics": r.metrics,
    }
