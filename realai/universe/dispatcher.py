"""Universal Agent Dispatcher — route tasks to hive agents across worlds."""
from __future__ import annotations

from typing import Any, Dict, Optional

_ROUTES = [
    (("code", "debug", "refactor", "implement", "patch"), "coder"),
    (("architect", "design", "structure", "layout"), "architect"),
    (("analy", "summar", "explain", "review"), "analyst"),
    (("memory", "recall", "remember", "embed"), "memory"),
    (("govern", "policy", "risk", "safety"), "governor"),
    (("route", "dispatch", "triage"), "router"),
    (("heal", "repair", "doctor"), "self-heal"),
    (("plan",), "planner"),
    (("guard", "secure"), "guardian"),
]


def route(task: str, world_id: Optional[str] = None) -> Dict[str, Any]:
    text = (task or "").strip().lower()
    agent = "overseer"
    reason = "default overseer"
    for keys, aid in _ROUTES:
        if any(k in text for k in keys):
            agent = aid
            reason = f"matched {keys}"
            break
    return {
        "ok": True,
        "name": "Universal Agent Dispatcher",
        "task": task,
        "world_id": world_id or "world-0",
        "agent_id": agent,
        "reason": reason,
        "note": "Static routing table. Does not invoke agents or heal.",
    }


def status() -> Dict[str, Any]:
    return {
        "ok": True,
        "name": "Universal Agent Dispatcher",
        "present": True,
        "routes": [{"keys": list(k), "agent": a} for k, a in _ROUTES],
    }