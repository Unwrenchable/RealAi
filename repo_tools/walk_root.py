#!/usr/bin/env python3
"""
Walk RealAI at any nesting depth — keeps going deeper into every folder.

  python tools/walk_root.py
  python tools/walk_root.py --deepen
  python tools/walk_root.py --start imports/external/unique-modules --deepen
  python tools/walk_root.py --root C:\\RealAI-clean --out scan_results/realai_root_walk.json

Craft: /walk force · /walk deepen · /walk imports/external
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT_DEFAULT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Recursive nested root walk (deeper and deeper) + unify map"
    )
    ap.add_argument("--root", default=str(ROOT_DEFAULT), help="Repo root")
    ap.add_argument(
        "--start",
        default="",
        help="Optional folder under root to start from (still recurses to leaves)",
    )
    ap.add_argument(
        "--out",
        default="",
        help="Output JSON (default: <root>/scan_results/realai_root_walk.json)",
    )
    ap.add_argument("--max-modules", type=int, default=12000)
    ap.add_argument(
        "--deepen",
        action="store_true",
        help="AST/signal-scan gold + imports/external nests (still skips bulk recovered/)",
    )
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    out = Path(args.out) if args.out else root / "scan_results" / "realai_root_walk.json"
    if not out.is_absolute():
        out = root / out

    start = None
    if args.start:
        start = Path(args.start)
        if not start.is_absolute():
            start = root / start
        start = start.resolve()
        if not start.exists():
            print(f"[RootWalker] start not found: {start}", file=sys.stderr)
            return 1

    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from core.realai_root_walker import RealAIRootWalker

    print(
        f"[RootWalker] walking start={start or root} deepen={args.deepen} …"
    )
    payload = RealAIRootWalker(
        root,
        out,
        max_modules=args.max_modules,
        deepen=bool(args.deepen),
        start=start,
    ).run()
    print(f"[RootWalker] wrote {out}")
    print(f"[RootWalker] map  {payload.get('map_md')}")
    deepest = payload.get("deepest_nests") or []
    print(
        f"[RootWalker] dirs={payload.get('scanned_dirs')} "
        f"max_depth={payload.get('max_depth_seen')} "
        f"modules={payload.get('module_count')} "
        f"nests={payload.get('nested_folder_count')} "
        f"leaf_nests={len(payload.get('leaf_nests') or [])} "
        f"scripts={payload.get('runnable_script_count')} "
        f"js={payload.get('js_file_count')} json={payload.get('json_file_count')} "
        f"dupes={payload.get('unify', {}).get('duplicate_basename_count')}"
    )
    for n in deepest[:8]:
        print(
            f"  deepest> depth={n.get('depth')} code={n.get('code_top')} `{n.get('rel')}`"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
