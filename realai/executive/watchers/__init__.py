"""Executive watchers - one goal type per module.

Registered watchers (static scaffolds; no auto-start):
- repo_health
- rackup_health
- caps_watch
"""
from __future__ import annotations

from realai.executive.loop import ExecutiveLoop

WATCHER_NAMES = (
    "repo_health",
    "rackup_health",
    "caps_watch",
)


def attach_all(loop: ExecutiveLoop) -> None:
    """Register all known watcher act/judge handlers on an ExecutiveLoop."""
    from realai.executive.watchers import caps_watch, rackup_health, repo_health

    repo_health.attach(loop)
    rackup_health.attach(loop)
    caps_watch.attach(loop)


__all__ = ["attach_all", "WATCHER_NAMES"]