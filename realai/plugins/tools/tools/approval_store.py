"""Compatibility shim (nested tools/tools copy): loads ``realai/plugins/tools/approval_store.py`` by path.

Loaded by path rather than ``import realai.plugins.tools.approval_store`` because sibling scripts here use
``from approval_store import ...`` with only this directory on sys.path, and the realai.plugins.tools package
__init__ is not importable outside the server. Same store, same API (one approvals file).
"""
from __future__ import annotations

import importlib.util as _ilu
from pathlib import Path as _Path

_spec = _ilu.spec_from_file_location("_realai_approval_store_canonical", _Path(__file__).resolve().parents[1] / "approval_store.py")
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

for _n in ("create_request", "list_requests", "update_request", "get_request", "annotate_request", "_load", "_save",
           "_resolve_store", "_DEFAULT_STORE"):
    globals()[_n] = getattr(_mod, _n)
