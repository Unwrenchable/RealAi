#!/usr/bin/env python3
"""
Deep unify pipeline:
  1) Recursive root walk (deeper and deeper into every folder)
  2) Re-walk the deepest nest folders individually
  3) Organize/patch/merge deepest sources → proper locations
  4) Auto-wire abilities registry

  python scripts/deep_unify_walk.py
  python scripts/deep_unify_walk.py --apply
  python scripts/deep_unify_walk.py --apply --max-nests 40
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Deep nested walk → unify → organize → wire")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--apply", action="store_true", help="Apply organize copies/merges")
    ap.add_argument("--max-nests", type=int, default=25, help="Deepest nests to re-walk")
    ap.add_argument("--organize-limit", type=int, default=800)
    ap.add_argument("--skip-wire", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    from core.realai_root_walker import RealAIRootWalker
    from core.repo_organizer import run_organize

    out_main = root / "scan_results" / "realai_root_walk.json"
    print(f"[deep-unify] phase1 root walk deepen=True → {out_main}")
    payload = RealAIRootWalker(root, out_main, deepen=True).run()
    deepest = list(payload.get("deepest_nests") or [])[: max(1, args.max_nests)]
    print(
        f"[deep-unify] max_depth={payload.get('max_depth_seen')} "
        f"nests={payload.get('nested_folder_count')} "
        f"re-walking top {len(deepest)} deepest folders"
    )

    nest_reports = []
    nests_dir = root / "scan_results" / "deep_nests"
    nests_dir.mkdir(parents=True, exist_ok=True)
    for i, nest in enumerate(deepest, 1):
        rel = nest.get("rel") or ""
        start = root / rel
        if not start.is_dir():
            continue
        out_n = nests_dir / f"nest_{i:02d}_{Path(rel).name}.json"
        print(f"[deep-unify] nest {i}/{len(deepest)} depth={nest.get('depth')} `{rel}`")
        try:
            sub = RealAIRootWalker(root, out_n, deepen=True, start=start).run()
            nest_reports.append(
                {
                    "rel": rel,
                    "depth": nest.get("depth"),
                    "scanned_dirs": sub.get("scanned_dirs"),
                    "module_count": sub.get("module_count"),
                    "js_file_count": sub.get("js_file_count"),
                    "json_file_count": sub.get("json_file_count"),
                    "runnable_script_count": sub.get("runnable_script_count"),
                    "out": str(out_n),
                }
            )
        except Exception as e:
            nest_reports.append({"rel": rel, "error": str(e)})

    # Refresh main walk index (keeps deepest_nests) then organize deepest-first
    print(f"[deep-unify] phase3 organize apply={args.apply}")
    org = run_organize(
        root=root,
        apply=bool(args.apply),
        limit=int(args.organize_limit),
        refresh_walk=False,
    )

    wire = None
    if not args.skip_wire:
        print("[deep-unify] phase4 auto_wire abilities")
        try:
            import abilities.auto_wire as aw

            # auto_wire uses relative paths from cwd
            import os

            prev = os.getcwd()
            try:
                os.chdir(root)
                if hasattr(aw, "main"):
                    aw.main()
                elif hasattr(aw, "run"):
                    aw.run()
                else:
                    # execute module as script
                    import runpy

                    runpy.run_path(str(root / "abilities" / "auto_wire.py"), run_name="__main__")
            finally:
                os.chdir(prev)
            wire = {"ok": True, "registry": "realai/abilities/registry.json"}
        except SystemExit as e:
            wire = {"ok": int(getattr(e, "code", 0) or 0) == 0, "exit": getattr(e, "code", 0)}
        except Exception as e:
            wire = {"ok": False, "error": str(e)}

    summary = {
        "version": 1,
        "at": utc(),
        "root": str(root),
        "apply": bool(args.apply),
        "max_depth_seen": payload.get("max_depth_seen"),
        "nested_folder_count": payload.get("nested_folder_count"),
        "deepest_rewalked": nest_reports,
        "organize": {
            "summary": org.get("summary"),
            "actions": org.get("actions"),
            "path": org.get("path"),
        },
        "wire": wire,
        "walk": str(out_main),
        "map_md": payload.get("map_md"),
    }
    out = root / "scan_results" / "DEEP_UNIFY_REPORT.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md = root / "scan_results" / "DEEP_UNIFY_REPORT.md"
    lines = [
        "# Deep unify walk",
        "",
        f"- at: {summary['at']}",
        f"- apply: {args.apply}",
        f"- max_depth_seen: {summary['max_depth_seen']}",
        f"- nests: {summary['nested_folder_count']}",
        f"- organize: {org.get('summary')}",
        f"- wire: {wire}",
        "",
        "## Deepest re-walked",
    ]
    for n in nest_reports[:30]:
        if n.get("error"):
            lines.append(f"- `{n.get('rel')}` ERROR {n.get('error')}")
        else:
            lines.append(
                f"- depth={n.get('depth')} `{n.get('rel')}` "
                f"dirs={n.get('scanned_dirs')} py_mod={n.get('module_count')} "
                f"js={n.get('js_file_count')} json={n.get('json_file_count')}"
            )
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[deep-unify] report → {out}")
    print(f"[deep-unify] map    → {md}")
    print(f"[deep-unify] organize actions={org.get('actions')}")
    return 0 if (org.get("ok", True) and (wire is None or wire.get("ok", True))) else 1


if __name__ == "__main__":
    raise SystemExit(main())
