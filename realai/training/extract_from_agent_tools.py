"""Compatibility shim for realai.training.extract_from_agent_tools -> realai.core.training.extract_from_agent_tools.

Canonical merged version lives in realai/core/training (decision 2). Module object aliased.
"""
import sys as _sys

from realai.core.training import extract_from_agent_tools as _canonical

if __name__ == "__main__":
    _canonical.main()
else:
    _sys.modules[__name__] = _canonical
