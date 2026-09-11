"""Package-root import shim for Critique engine.

Gold lives at ``realai.core.critique`` after the 2026-08-30 package-root sort.
This module re-exports that gold. Do not put logic here.
"""
from __future__ import annotations

from realai.core.critique import *  # noqa: F403
