"""Package-root import shim for Guardian layer.

Gold lives at ``realai.core.guardian`` after the 2026-08-30 package-root sort.
This module re-exports that gold. Do not put logic here.
"""
from __future__ import annotations

from realai.core.guardian import *  # noqa: F403
