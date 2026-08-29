"""Canonical alias: deep_gold. Recovered: dds3_deep_gold_map.py"""
from __future__ import annotations
STATUS = "recovered_alias"
try:
    from dds3_deep_gold_map import *  # noqa
except ImportError:
    from .dds3_deep_gold_map import *  # type: ignore  # noqa
