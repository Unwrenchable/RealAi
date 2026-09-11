"""
Canonical orchestrator entry — delegates to the live v3 runtime.

This module exists so imports / launchers that expect ``realai_orchestrator``
resolve to ``realai.v3_orchestrator`` instead of an empty stub.

Run:
  python -m realai.realai_orchestrator --host 127.0.0.1 --port 8001
"""

from __future__ import annotations

from realai.v3_orchestrator import *  # noqa: F403
from realai.v3_orchestrator import main

if __name__ == "__main__":
    raise SystemExit(main())
