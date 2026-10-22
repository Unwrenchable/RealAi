"""DEPRECATED shim (2026-10-22): forwards to the canonical engine `realai.agentx.executor`.

The previous fork is kept unchanged as `executor_legacy.py` for anything that
needs a name only it defines. New code should import `realai.agentx.executor` directly.
"""
from realai.agentx.executor import *  # noqa: F401,F403
import importlib as _importlib

_canon = _importlib.import_module("realai.agentx.executor")


def __getattr__(name):
    if name.startswith("__"):
        raise AttributeError(name)
    try:
        return getattr(_canon, name)
    except AttributeError:
        _legacy = _importlib.import_module(__name__ + "_legacy")
        return getattr(_legacy, name)
