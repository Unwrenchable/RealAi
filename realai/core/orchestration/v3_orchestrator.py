"""Shim — live v3 HTTP orch gold lives in ``realai.orchestration.v3_orchestrator``.

Do not grow a second :8001 server under ``core.orchestration``.
"""

from __future__ import annotations

from realai.orchestration.v3_orchestrator import *  # noqa: F403
from realai.orchestration.v3_orchestrator import main

__all__ = ["main"]
