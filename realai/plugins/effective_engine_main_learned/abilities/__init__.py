"""Learned module ability stubs (auto-discover *.py)."""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Callable

# REALAI_LEARNED_STUB

ABILITY_RUNNERS: dict[str, Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]] = {}


def _load() -> None:
    here = Path(__file__).resolve().parent
    pkg = __package__ or ""
    for path in sorted(here.glob("*.py")):
        if path.name.startswith("_"):
            continue
        mod = importlib.import_module(f".{path.stem}", pkg)
        run = getattr(mod, "run", None)
        if not callable(run):
            continue
        ABILITY_RUNNERS[path.stem] = run
        for alias in getattr(mod, "ALIASES", ()) or ():
            ABILITY_RUNNERS[str(alias)] = run
    if "health" in ABILITY_RUNNERS:
        ABILITY_RUNNERS.setdefault("ping", ABILITY_RUNNERS["health"])


_load()


def run_ability(
    name: str,
    player: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    key = (name or "health").strip().lower()
    fn = ABILITY_RUNNERS.get(key)
    if not fn:
        return {
            "error": f"unknown ability '{name}'",
            "available": sorted(set(ABILITY_RUNNERS)),
        }
    return fn(player or {}, payload or {})


__all__ = ["ABILITY_RUNNERS", "run_ability"]
