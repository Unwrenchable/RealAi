"""Placeholder for agent_tools/engine/__init__.py — listed in SOURCES.txt, source missing from disk.
Recover from git history or bytecode when available.
RECOVERY_STATUS = "missing_source"
"""
RECOVERY_STATUS = "missing_source"
MODULE = 'agent_tools/engine/__init__.py'

# 2026-10-17: this package shadows the shim realai/engine.py ("re-export realai.core.engine"), so
# ``from realai.engine import X`` found nothing. Fall back to realai.core.engine lazily (no import-time
# side effects; submodules executor/loader/memory/... still resolve normally). See docs/BUILD_LEFTOVERS.md.


def __getattr__(name):
    if name.startswith("__"):
        raise AttributeError(name)
    import importlib

    core = importlib.import_module("realai.core.engine")
    try:
        return getattr(core, name)
    except AttributeError:
        raise AttributeError(f"module 'realai.engine' has no attribute {name!r}") from None
