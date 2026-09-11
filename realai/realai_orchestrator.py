"""Package-root import shim for the canonical orchestrator entry.

Gold lives at ``realai.orchestration.v3_orchestrator`` (via realai.v3_orchestrator).
Supports ``python -m realai.realai_orchestrator``.
"""
from __future__ import annotations

import sys
from pathlib import Path

_pkg = Path(__file__).resolve().parent
_root = _pkg.parent
for _p in (str(_root), str(_pkg)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from realai.orchestration.v3_orchestrator import *  # noqa: F403
from realai.orchestration.v3_orchestrator import main

if __name__ == "__main__":
    raise SystemExit(main())
