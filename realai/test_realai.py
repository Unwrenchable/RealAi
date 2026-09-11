"""Package-root import shim for RealAI smoke test.

Gold lives at ``realai.tests.test_realai`` after the 2026-08-30 package-root sort.
This module re-exports that gold. Do not put logic here.
"""
from __future__ import annotations

from realai.tests.test_realai import *  # noqa: F403
