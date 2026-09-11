"""RealAI Universe Mode — highest-level orchestration layer.

Treats every workspace, repo, module, and agent as part of one unified universe.
Repos are worlds; workspaces are dimensions; agents are entities.

Static reconstruction aligned to Travis Universe Mode docs (2026-09-07).
"""
from __future__ import annotations

from realai.universe.mode import is_universe_on, universe_status

__all__ = ["is_universe_on", "universe_status"]