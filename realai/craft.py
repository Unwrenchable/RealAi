"""Compatibility shim for realai.craft -> realai.cli.craft (canonical; ``realai-craft = realai.cli.craft:main``).

Merge 2026-10-16 (decision 2): realai/craft.py (3233 lines, last change 2026-09-24) was an older phase of
realai/cli/craft.py (4113 lines, 2026-09-27). Every def it had exists in the canonical file; cli/craft.py adds 23
(is_protected_core_path, tool_learn/_auto/_queue, fingerprint_stack, _keyword_grep_pattern, _should_auto_inspect, ...)
and refines the 17 shared ones (ranked grep, Nest player/payload mapping in tool_rackup, status-tool LLM skip).
The module object is aliased so ``import realai.craft`` and every name (public or private) resolve to the canonical.
"""
import sys as _sys

from realai.cli import craft as _canonical

if __name__ == "__main__":
    _sys.exit(_canonical.main(_sys.argv[1:]))
else:
    _sys.modules[__name__] = _canonical
