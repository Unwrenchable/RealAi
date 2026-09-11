"""Compat shim — authority is ``realai.plugins``.

Root ``plugins/`` was a near-identical twin. Import the live package::

    import realai.plugins
    from realai.plugins import ...
"""
from __future__ import annotations

import importlib
import sys

_auth = importlib.import_module("realai.plugins")
sys.modules[__name__] = _auth
