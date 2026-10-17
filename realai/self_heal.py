"""Compatibility shim for realai.self_heal (the historically wired path) -> realai.core.self_heal (canonical per AUTHORITY.md: self-heal lives in realai/core).

The module object is aliased, so every public and private name (status, run_*, _probe_routes, _run_py, _ROOT, ...)
and any monkeypatching keep working. Promote apply now goes through realai.core.approval_gate.
"""
import sys as _sys

from realai.core import self_heal as _canonical

_sys.modules[__name__] = _canonical
