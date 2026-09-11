"""Package-root import shim for Plugin marketplace.

Gold lives at ``realai.plugins.plugin_marketplace`` after the 2026-08-30 package-root sort.
This module re-exports that gold. Do not put logic here.
"""
from __future__ import annotations

from realai.plugins.plugin_marketplace import *  # noqa: F403
