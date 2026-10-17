"""Compatibility shim for realai.plugins.realai_local_server -> realai.server.realai_local_server (canonical, decision 1: servers live in realai/server).

Older llama-cli shim with hardcoded C:\\llama.cpp / OneDrive model paths; canonical discovers llama-cli and GGUFs.
Module object aliased, so every public/private name and monkeypatching resolve to the canonical module.
"""
import sys as _sys

from realai.server import realai_local_server as _canonical

if __name__ == "__main__":
    import runpy

    runpy.run_module("realai.server.realai_local_server", run_name="__main__")
else:
    _sys.modules[__name__] = _canonical
