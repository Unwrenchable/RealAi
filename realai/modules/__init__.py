"""Compat shim — authority is repo-root ``modules`` (not ``realai.modules``)."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_auth = importlib.import_module("modules")
sys.modules[__name__] = _auth
