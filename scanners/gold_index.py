"""Canonical alias: gold_index. Recovered: scanners/assemble_gold_index.py"""
from __future__ import annotations
STATUS = "recovered_alias"
CANONICAL_NAME = "gold_index"
RECOVERED_FROM = "scanners/assemble_gold_index.py"
try:
    from assemble_gold_index import *  # noqa: F401,F403
except ImportError:
    from .assemble_gold_index import *  # type: ignore  # noqa: F401,F403
