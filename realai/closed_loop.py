"""Package-root import shim for Closed self-improve loop.

Gold lives at ``realai.core.closed_loop`` after the 2026-08-30 package-root sort.
This module re-exports that gold. Do not put logic here.
"""
from __future__ import annotations

from realai.core.closed_loop import *  # noqa: F403
