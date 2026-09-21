"""RealAI package root.

Hive / live stack lives in ``realai.hive`` and ``realai.orchestration``.
The v1 SDK client classes stay in ``realai._v1_client`` and are re-exported
here so ``from realai import RealAI, RealAIClient`` keeps working.

Do not import v3_orchestrator at module import time.
"""
from __future__ import annotations

from typing import Any

from realai._v1_client import RealAI, RealAIClient

__all__ = [
    "RealAI",
    "RealAIClient",
    "coverage",
    "hive_status",
    "register_plugins",
    "run_hive",
]


def hive_status() -> dict[str, Any]:
    from realai.hive import hive_status as _hive_status

    return _hive_status()


def run_hive(task: str, agent: str = "researcher") -> dict[str, Any]:
    from realai.hive import run_hive as _run_hive

    return _run_hive(task, agent=agent)


def register_plugins(model: Any = None) -> list[dict[str, Any]]:
    from realai.hive import register_plugins as _register_plugins

    return _register_plugins(model)


def coverage() -> dict[str, Any]:
    from realai.hive import coverage as _coverage

    return _coverage()


def __getattr__(name: str) -> Any:
    # Lazy escape hatch for rarely used dump symbols without importing orch at import time.
    if name in {"RealAI", "RealAIClient"}:
        from realai import _v1_client

        return getattr(_v1_client, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
