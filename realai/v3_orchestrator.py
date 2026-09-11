"""Package-root import shim for the v3 orchestrator.

Launchers and Craft import ``realai.v3_orchestrator``. Gold lives at
``realai.orchestration.v3_orchestrator``. This dest-empty module re-exports
that gold and supports ``python -m realai.v3_orchestrator --host --port``.
Do not put logic here.
"""
from __future__ import annotations

import sys
from pathlib import Path

_pkg = Path(__file__).resolve().parent  # .../realai
_root = _pkg.parent  # product home (e.g. C:\RealAI-clean)
for _p in (str(_root), str(_pkg)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from realai.orchestration.v3_orchestrator import *  # noqa: F403
from realai.orchestration.v3_orchestrator import main

if __name__ == "__main__":
    raise SystemExit(main())
