"""Package-root import shim for Identity layer.

Gold lives at ``realai.core.identity`` after the 2026-08-30 package-root sort.
This module re-exports that gold. Do not put logic here.
"""
from __future__ import annotations

from realai.core.identity import *  # noqa: F403
