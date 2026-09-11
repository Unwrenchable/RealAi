"""Package-root import shim for Nested model catalog facade.

Gold lives at ``realai.models.nested_realai_model_catalog`` after the 2026-08-30 package-root sort.
This module re-exports that gold. Do not put logic here.
"""
from __future__ import annotations

from realai.models.nested_realai_model_catalog import *  # noqa: F403
