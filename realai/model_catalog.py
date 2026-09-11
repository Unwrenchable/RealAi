"""Package-root import shim for the model catalog.

Craft and the v3 orchestrator import ``realai.model_catalog``. Gold lives at
``realai.models.model_catalog`` after the 2026-08-30 package-root sort.
This module re-exports that gold. Do not put logic here.
"""
from __future__ import annotations

from realai.models.model_catalog import *  # noqa: F403
