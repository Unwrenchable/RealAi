"""Shim — live hive router gold lives in ``realai.orchestration.hive_router``."""

from __future__ import annotations

from realai.orchestration.hive_router import (  # noqa: F401
    ROLE_MODEL_TABLE,
    list_nest_orchestrators,
    load_github_hive_agents,
    register_routes,
    route_model,
    run_cycle,
)

__all__ = [
    "ROLE_MODEL_TABLE",
    "list_nest_orchestrators",
    "load_github_hive_agents",
    "register_routes",
    "route_model",
    "run_cycle",
]
