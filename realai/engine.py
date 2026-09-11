"""Package-root import shim for Core engine.

Gold lives at ``realai.core.engine`` after the 2026-08-30 package-root sort.
This module re-exports that gold. Do not put logic here.
"""
from __future__ import annotations

from realai.core.engine import *  # noqa: F403
