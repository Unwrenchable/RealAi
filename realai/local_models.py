"""Package-root import shim for Local model manager.

Gold lives at ``realai.core.local_models`` after the 2026-08-30 package-root sort.
This module re-exports that gold. Do not put logic here.
"""
from __future__ import annotations

from realai.core.local_models import *  # noqa: F403
