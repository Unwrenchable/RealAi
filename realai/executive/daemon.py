"""Static executive daemon entry - persistent-ready, no auto-start on import.

User-callable later (document only during reconstruction)::

    python -m realai.executive.daemon --once

Loads goals, runs registered watchers once or on an interval, appends evidence
via ExecutiveLoop, and writes ``state/executive_status.json``.

Hard constraints for this module:
- Safe if imported (no side effects at import time).
- No network, heal, training, or RealAI runtime start.
- Interval from env REALAI_EXEC_INTERVAL_S (default 3600).
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from realai.executive.goal import load_goals
from realai.executive.loop import ExecutiveLoop

DEFAULT_INTERVAL_S = 3600
STATUS_FILENAME = "executive_status.json"


def default_workspace() -> Path:
    return Path(os.environ.get("REALAI_WORKSPACE") or r"C:\RealAI-clean")


def status_path(workspace: Path) -> Path:
    d = workspace / "realai" / "executive" / "state"
    d.mkdir(parents=True, exist_ok=True)
    return d / STATUS_FILENAME


def build_loop(workspace: Path) -> ExecutiveLoop:
    """Construct loop and attach all registered watchers (static import)."""
    from realai.executive.watchers import attach_all

    loop = ExecutiveLoop(workspace)
    attach_all(loop)
    return loop


def write_status(workspace: Path, payload: Dict[str, Any]) -> Path:
    path = status_path(workspace)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def run_cycle(loop: ExecutiveLoop, workspace: Path) -> Dict[str, Any]:
    """Load goals, tick open ones (evidence + verdict), write status snapshot."""
    goals = load_goals(workspace)
    results = loop.run_once()
    # Re-load after ticks so status reflects latest goal rows
    goals_after = load_goals(workspace)
    open_ids = [g.id for g in goals_after if g.status in {"open", "acting", "verifying", "failed"}]
    payload: Dict[str, Any] = {
        "ts": time.time(),
        "workspace": str(workspace),
        "mode": "cycle",
        "goal_count_before": len(goals),
        "goal_count": len(goals_after),
        "open_goal_ids": open_ids,
        "results": results,
        "interval_s": int(os.environ.get("REALAI_EXEC_INTERVAL_S", str(DEFAULT_INTERVAL_S))),
        "watchers": sorted(loop.handlers.keys()),
        "note": "Static executive status. Daemon does not start heal or network.",
    }
    write_status(workspace, payload)
    return payload


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="realai.executive.daemon",
        description="Persistent-ready executive daemon entry (no auto-start on import).",
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Run a single act/sense/judge cycle then exit (no sleep loop).",
    )
    p.add_argument(
        "--workspace",
        default=None,
        help=r"Workspace root (default: REALAI_WORKSPACE or C:\RealAI-clean).",
    )
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry. Call explicitly; never invoked at import time."""
    args = parse_args(argv)
    workspace = Path(args.workspace) if args.workspace else default_workspace()
    loop = build_loop(workspace)
    # Ensure goals are loaded (and state dir exists via goals_path side effects in loaders)
    load_goals(workspace)

    if args.once:
        run_cycle(loop, workspace)
        return 0

    interval = int(os.environ.get("REALAI_EXEC_INTERVAL_S", str(DEFAULT_INTERVAL_S)))
    if interval < 1:
        interval = DEFAULT_INTERVAL_S
    while True:
        run_cycle(loop, workspace)
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())