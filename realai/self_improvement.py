"""Package-root import shim for the self-improvement engine.

Launchers and Craft import ``realai.self_improvement``. Gold lives at
``realai.core.self_improvement`` after the 2026-08-30 package-root sort.
This module re-exports that gold. Do not put logic here.
"""
from __future__ import annotations

from realai.core.self_improvement import *  # noqa: F403
