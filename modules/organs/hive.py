"""Hive — discover and invoke all synthetic organs."""
from __future__ import annotations

import importlib
import pkgutil
from typing import Any

from modules.organs.base import Organ, OrganContext, OrganResult

_CATEGORIES = (
    "cognitive",
    "nervous",
    "dream",
    "body",
    "metabolic",
    "evolution",
    "memory_ecosystem",
    "meta",
)


def _iter_organ_modules():
    import modules.organs as pkg

    for cat in _CATEGORIES:
        try:
            sub = importlib.import_module(f"modules.organs.{cat}")
        except Exception:
            continue
        prefix = sub.__name__ + "."
        path = getattr(sub, "__path__", None)
        if not path:
            continue
        for m in pkgutil.iter_modules(path, prefix):
            if m.name.rsplit(".", 1)[-1] in ("__init__", "base", "hive"):
                continue
            yield m.name


def load_all_organs() -> dict[str, Organ]:
    organs: dict[str, Organ] = {}
    for modname in _iter_organ_modules():
        try:
            mod = importlib.import_module(modname)
            factory = getattr(mod, "create_organ", None)
            if not callable(factory):
                continue
            organ = factory()
            organs[organ.id] = organ
        except Exception:
            continue
    return organs


def list_organs() -> list[dict[str, Any]]:
    return [o.info() for o in load_all_organs().values()]


def get_organ(organ_id: str) -> Organ | None:
    organs = load_all_organs()
    if organ_id in organs:
        return organs[organ_id]
    # allow bare id without organ. prefix
    key = organ_id if organ_id.startswith("organ.") else f"organ.{organ_id}"
    return organs.get(key)


def call_organ(organ_id: str, goal: str = "", payload: dict | None = None) -> OrganResult:
    organ = get_organ(organ_id)
    if organ is None:
        return OrganResult(organ_id=organ_id, ok=False, notes="organ not found")
    return organ.process(OrganContext(goal=goal, payload=payload or {}))


def hive_status() -> dict[str, Any]:
    organs = load_all_organs()
    by_cat: dict[str, int] = {}
    for o in organs.values():
        by_cat[o.category] = by_cat.get(o.category, 0) + 1
    return {
        "organ_count": len(organs),
        "expected": 44,
        "complete": len(organs) >= 44,
        "by_category": by_cat,
        "ids": sorted(organs.keys()),
    }
