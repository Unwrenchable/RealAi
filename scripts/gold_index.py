"""
Canonical alias: gold_index
=============================
Recovered implementation: scanners/assemble_gold_index.py

This module re-exports the recovered source under the canonical name
requested by the RealAI-clean reconstruction. Import is static; nothing
is executed at module import besides the recovered module body.
"""
from __future__ import annotations

STATUS = "recovered_alias"
CANONICAL_NAME = "gold_index"
RECOVERED_FROM = 'scanners/assemble_gold_index.py'

try:
    from assemble_gold_index import *  # noqa: F401,F403
except ImportError:
    # Relative package import when loaded as scanners.gold_index
    from .assemble_gold_index import *  # type: ignore  # noqa: F401,F403
