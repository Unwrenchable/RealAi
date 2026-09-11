"""Shim: plugins copy re-exports the canonical ability catalog.

Keep a single source of truth at ``realai.ability_catalog`` so LIVE/PARTIAL
status cannot drift between package roots.
"""
from __future__ import annotations

from realai.ability_catalog import *  # noqa: F403
from realai.ability_catalog import (  # noqa: F401
    RUNDOWN_ABILITIES,
    build_catalog,
    coverage_summary,
)
