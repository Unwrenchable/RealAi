"""Compatibility shim for realai.plugins.api_big_server -> realai.server.legacy_api (canonical, decision 1: servers live in realai/server).

Big-server phase (1267 lines): its only unique route, POST /v1/memory/recall, is merged into the canonical.
Module object aliased, so every public/private name and monkeypatching resolve to the canonical module.
"""
import sys as _sys

from realai.server import legacy_api as _canonical

if __name__ == "__main__":
    _sys.exit(_canonical.main())
else:
    _sys.modules[__name__] = _canonical
