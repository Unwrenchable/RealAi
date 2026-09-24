"""RealAI orchestration agents package.

Canonical implementation lives in ``modules.orchestrators`` / ``realai.orchestration``.
This package exists so ``agents.orchestration`` imports resolve cleanly.
"""
from __future__ import annotations

try:
    from modules.orchestrators import *  # noqa: F403
except Exception:  # pragma: no cover
    from realai.orchestration import *  # type: ignore  # noqa: F403

__all__ = [name for name in globals() if not name.startswith("_")]
