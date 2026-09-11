"""
Canonical alias: dds3
=============================
Recovered implementation: scanners/dds3_deep_gold_map.py

This module re-exports the recovered source under the canonical name
requested by the RealAI-clean reconstruction. Import is static; nothing
is executed at module import besides the recovered module body.
"""
from __future__ import annotations

STATUS = "recovered_alias"
CANONICAL_NAME = "dds3"
RECOVERED_FROM = 'scanners/dds3_deep_gold_map.py'

try:
    from dds3_deep_gold_map import *  # noqa: F401,F403
except ImportError:
    # Relative package import when loaded as scanners.dds3
    from .dds3_deep_gold_map import *  # type: ignore  # noqa: F401,F403
