"""Package-root import shim for Desktop GUI.

Gold lives at ``realai.ui.realai_gui`` after the 2026-08-30 package-root sort.
This module re-exports that gold. Do not put logic here.
"""
from __future__ import annotations

from realai.ui.realai_gui import *  # noqa: F403
