"""Public RealAI hive surface.

Prefer this module over importing the 421 KB package-root ``realai/__init__.py``
dump when you want the live hive (v3 orchestrator, plugins, organs, catalog).

The dump remains for ``from realai import RealAI`` (v1 SDK client).
"""
from __future__ import annotations

from typing import Any

__all__ = [
    "coverage",
    "hive_status",
    "register_plugins",
    "run_hive",
    "tools",
]


def tools() -> list[dict[str, Any]]:
    from realai.v3_runtime_bridge import tools_catalog

    return list(tools_catalog() or [])


def hive_status() -> dict[str, Any]:
    from realai.orchestration.hive_router import register_routes

    return register_routes()


def run_hive(task: str, agent: str = "researcher") -> dict[str, Any]:
    from realai.orchestration.hive_router import run_cycle

    return run_cycle(task, agent=agent)


def register_plugins(model: Any = None) -> list[dict[str, Any]]:
    from realai.plugins import register_all

    return register_all(model)


def coverage() -> dict[str, Any]:
    from realai.ability_catalog import coverage_summary

    return coverage_summary()
