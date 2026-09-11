#!/usr/bin/env python3
"""
Organize nested/mis-homed .py/.js/.json into proper RealAI locations.

  python scripts/organize_repo.py              # dry-run plan
  python scripts/organize_repo.py --apply      # copy/merge safely
  python scripts/organize_repo.py --refresh-walk --apply

Never deletes nests. JSON shallow-merges (dest wins on key conflict).
Code copies only if dest missing or dest is smaller.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Organize RealAI nests into proper locations")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--apply", action="store_true", help="Write copies/merges (default dry-run)")
    ap.add_argument("--refresh-walk", action="store_true", help="Re-run root walker first")
    ap.add_argument("--limit", type=int, default=500)
    args = ap.parse_args(argv)

    from core.repo_organizer import run_organize

    result = run_organize(
        root=Path(args.root),
        apply=bool(args.apply),
        limit=int(args.limit),
        refresh_walk=bool(args.refresh_walk),
    )
    print(result.get("summary"))
    print(f"[organize] plan → {result.get('path')}")
    print(f"[organize] map  → {result.get('map_md')}")
    actions = result.get("actions") or {}
    for k, v in sorted(actions.items()):
        print(f"  {k}: {v}")
    # show a few would_copy lines
    shown = 0
    for r in result.get("results") or []:
        if r.get("action", "").startswith("would") or r.get("action") in {
            "copied",
            "copied_enrich",
            "merged_json",
            "copied_json",
        }:
            print(f"  - {r.get('action')}: {r.get('src')} → {r.get('dest')} ({r.get('reason')})")
            shown += 1
            if shown >= 25:
                break
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
