"""Package-root import shim for the deepen cycle.

Self-heal and Craft import ``realai.deepen_cycle``. Gold lives at
``realai.core.deepen_cycle`` after the 2026-08-30 package-root sort.
This module re-exports that gold. Do not put logic here.
"""
from __future__ import annotations

from realai.core.deepen_cycle import *  # noqa: F403
from realai.core.deepen_cycle import main

if __name__ == "__main__":
    raise SystemExit(main())
