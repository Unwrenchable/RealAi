"""Package-root import shim for Hierarchical supervisor.

Gold lives at ``realai.core.supervisor`` after the 2026-08-30 package-root sort.
This module re-exports that gold. Do not put logic here.
"""
from __future__ import annotations

from realai.core.supervisor import *  # noqa: F403
