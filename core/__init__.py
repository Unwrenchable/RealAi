"""Product-root ``core`` compat package.

Live gold is ``realai.core``. Older abilities and nest routers still do
``from core.orchestration...`` / ``from core.plugins``. This package exists so
those imports resolve to the same gold without a second engine tree.
"""
from __future__ import annotations

from realai.core import *  # noqa: F403
