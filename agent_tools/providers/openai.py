"""DEPRECATED shim (2026-10-22): forwards to the canonical engine `realai.agentx.providers.openai`.

The previous fork is kept unchanged as `openai_legacy.py` for anything that
needs a name only it defines. New code should import `realai.agentx.providers.openai` directly.
"""
from realai.agentx.providers.openai import *  # noqa: F401,F403
import importlib as _importlib

_canon = _importlib.import_module("realai.agentx.providers.openai")


def __getattr__(name):
    if name.startswith("__"):
        raise AttributeError(name)
    try:
        return getattr(_canon, name)
    except AttributeError:
        _legacy = _importlib.import_module(__name__ + "_legacy")
        return getattr(_legacy, name)
