"""Package-root import shim for Aura memory.

Abilities and the v3 orchestrator import ``realai.aura_memory``. Gold lives at
``realai.memory.aura_memory`` after the 2026-08-30 package-root sort.
This module re-exports that gold. Do not put logic here.
"""
from __future__ import annotations

from realai.memory.aura_memory import *  # noqa: F403
