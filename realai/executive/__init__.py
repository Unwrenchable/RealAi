"""Persistent executive loop — goals with evidence, not chat turns.

First slice: Repo Health Watcher. Static reconstruction of the frontal-cortex
continuity layer. Does not auto-start; does not run heal.
"""
from __future__ import annotations

from realai.executive.goal import Goal, load_goals, append_goal_event
from realai.executive.loop import ExecutiveLoop

__all__ = ["Goal", "load_goals", "append_goal_event", "ExecutiveLoop"]