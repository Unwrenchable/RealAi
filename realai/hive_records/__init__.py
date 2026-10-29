"""Hive record pipeline: schema validation + secret rejection for bot task records.

Named ``hive_records`` (not ``hive``) because ``realai/hive.py`` already exists and a
``realai/hive/`` package would shadow it.
"""
from __future__ import annotations

SCHEMA_VERSION = "hive.v1"

__all__ = ["SCHEMA_VERSION"]
