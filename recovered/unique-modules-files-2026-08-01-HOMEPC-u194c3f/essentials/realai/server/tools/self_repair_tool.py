"""
self_repair_tool — recovered capability surface.

No historical file named self_repair_tool.py found under Users\\tsmit.
Delegates to self_heal status/assemble/discover (desktop mode) for repair loops.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def repair(mode: str = "status") -> Dict[str, Any]:
    """
    mode: status | assemble | discover_desktop | cycle
    """
    out: Dict[str, Any] = {"tool": "self_repair_tool", "mode": mode}
    try:
        from realai import self_heal
    except Exception as e:
        return {**out, "status": "error", "error": str(e)}

    if mode == "status":
        out["result"] = self_heal.status()
        out["status"] = "ok"
    elif mode == "assemble":
        out["result"] = self_heal.run_assemble()
        out["status"] = "ok"
    elif mode in ("discover_desktop", "desktop"):
        out["result"] = self_heal.run_discover(mode="desktop")
        out["status"] = "ok"
    elif mode == "cycle":
        out["result"] = self_heal.run_full_cycle(apply_promote=False)
        out["status"] = "ok"
    else:
        out["status"] = "error"
        out["error"] = f"unknown mode {mode}"
    return out


def run(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    arguments = arguments or {}
    return repair(str(arguments.get("mode") or "status"))
