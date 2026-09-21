"""Compat shim — gold is ``realai.orchestration.hive_router``."""
from __future__ import annotations

from realai.orchestration.hive_router import *  # noqa: F403
from realai.orchestration.hive_router import (
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
