"""Compat shim — authority is repo-root ``abilities`` (not ``realai.abilities``)."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_AUTH = _ROOT / "abilities"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Re-export the authority package so ``import realai.abilities`` still works.
_auth = importlib.import_module("abilities")
sys.modules[__name__] = _auth
