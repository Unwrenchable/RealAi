"""Compatibility shim for realai.core.api_server -> realai.server.legacy_api (canonical, decision 1: servers live in realai/server).

Older phase (1340 lines): a strict subset of the canonical routes; lacked vulkan forward, fusion UI and CORS helpers.
Module object aliased, so every public/private name and monkeypatching resolve to the canonical module.
"""
import sys as _sys

from realai.server import legacy_api as _canonical

if __name__ == "__main__":
    _sys.exit(_canonical.main())
else:
    _sys.modules[__name__] = _canonical
