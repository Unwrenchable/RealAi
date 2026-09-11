"""Canonical import for the tool-calling protocol.

Prefer::

    from realai.tools import TOOL_REGISTRY, ToolSchema

This top-level ``tools`` package re-exports ``realai.tools`` so ``import tools``
does not pick up a random scripts folder.
Legacy helper scripts live in ``repo_tools/``.
"""
from __future__ import annotations

from realai.tools import *  # noqa: F403
from realai import tools as _rt

# Re-export module attributes
__all__ = [n for n in dir(_rt) if not n.startswith("_")]
