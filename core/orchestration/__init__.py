"""Compat: ``core.orchestration`` → ``realai.core.orchestration`` → live gold."""
from __future__ import annotations

from realai.core.orchestration import *  # noqa: F403
from realai.core.orchestration.hive_router import (  # noqa: F401
    list_nest_orchestrators,
    register_routes,
    route_model,
    run_cycle,
)

__all__ = [
    "list_nest_orchestrators",
    "register_routes",
    "route_model",
    "run_cycle",
]
