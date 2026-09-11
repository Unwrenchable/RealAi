"""Package-root import shim for Local self-builder.

Gold lives at ``realai.core.self_builder`` after the 2026-08-30 package-root sort.
This module re-exports that gold. Do not put logic here.
"""
from __future__ import annotations

from realai.core.self_builder import *  # noqa: F403
