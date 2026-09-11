#!/usr/bin/env python3
"""
Scan an external folder (e.g. D:\\from_accident) with deep walk and
produce a bring-back plan into RealAI-clean proper locations.

  python scripts/bring_back_from.py --src D:\\from_accident
  python scripts/bring_back_from.py --src D:\\from_accident --apply

Default = plan only (writes scan_results/BRING_BACK_*.json/md).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

REALAI = Path(__file__).resolve().parents[1]
if str(REALAI) not in sys.path:
    sys.path.insert(0, str(REALAI))

from core.realai_root_walker import RealAIRootWalker  # noqa: E402
from core.repo_organizer import (  # noqa: E402
    PATH_RULES,
    PRODUCT_TOP,
    BASENAME_DEST_DIR,
    NEST_RE,
    SKIP_DIR_NAMES,
    merge_json_files,
    sha256_file,
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def propose_into_realai(rel: str) -> Optional[Tuple[str, str, int]]:
    """
    Map a path relative to the external src root into a RealAI-clean dest.
    Returns (dest_rel, reason, score) or None.
    """
    rel_n = rel.replace("\\", "/").lstrip("./")
    if not rel_n:
        return None
    name = Path(rel_n).name
    suffix = Path(name).suffix.lower()
    if suffix not in {".py", ".js", ".cjs", ".mjs", ".json"}:
        return None
    if name.lower() in {"package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"}:
        return None

    score = 0
    low = rel_n.lower()

    # Signal boosts
    for kw, pts in (
        ("orchestrat", 8),
        ("ability", 7),
        ("specialist", 7),
        ("self_heal", 8),
        ("self_improve", 8),
        ("agent_tool", 7),
        ("world_model", 7),
        ("memory", 5),
        ("rackup", 6),
        ("glicko", 5),
        ("plugin", 5),
        ("device_selector", 9),
        ("secure_tool", 7),
        ("approval", 6),
        ("promote", 5),
        ("wire", 5),
        ("hive", 5),
        ("nest", 4),
        ("realai", 3),
        ("gold", 4),
    ):
        if kw in low or kw in name.lower():
            score += pts

    # Basename explicit
    if name in BASENAME_DEST_DIR:
        dest = f"{BASENAME_DEST_DIR[name]}/{name}"
        return dest, f"basename:{BASENAME_DEST_DIR[name]}", score + 10

    # Path rules → RealAI homes
    for rx, dest_dir in PATH_RULES:
        if rx.search(rel_n) or rx.search(name):
            if dest_dir == "abilities/rackup" and suffix == ".py":
                dest = f"abilities/rackup/{name}"
            elif dest_dir == "modules/orchestrators" and suffix == ".py":
                dest = f"modules/orchestrators/{name}"
            elif dest_dir == "scripts" and suffix == ".py":
                dest = f"scripts/{name}"
            elif dest_dir == "tools" and suffix in {".py", ".js", ".cjs", ".mjs"}:
                dest = f"tools/{name}"
            elif suffix == ".json":
                if "registry" in name.lower():
                    dest = f"realai/plugins/{name}"
                elif "agent" in name.lower():
                    dest = f"agents/agentx/{name}"
                else:
                    dest = f"scan_results/from_accident/{name}"
            elif suffix in {".js", ".cjs", ".mjs"}:
                dest = f"tools/{name}"
            else:
                dest = f"{dest_dir}/{name}"
            return dest, f"rule:{dest_dir}", score + 6

    # Generic salvage staging for still-interesting files
    if score >= 5:
        if suffix == ".py":
            if "tool" in low:
                dest = f"agent_tools/from_accident/{name}"
            elif "ability" in low or "agent" in low:
                dest = f"abilities/from_accident/{name}"
            else:
                dest = f"imports/external/from_accident/{name}"
        elif suffix == ".json":
            dest = f"scan_results/from_accident/{name}"
        else:
            dest = f"tools/from_accident/{name}"
        return dest, "score_staging", score

    return None


def collect_paths(src_root: Path, walk: Dict[str, Any]) -> List[str]:
    paths: List[str] = []
    for nest in list(walk.get("deepest_nests") or []) + list(walk.get("leaf_nests") or []):
        rel = (nest.get("rel") or "").replace("\\", "/")
        # walk was rooted at src_root, so nest rel is relative to src_root
        # but RealAIRootWalker stores rel relative to its `root` arg
        folder = src_root / rel if rel not in ("", ".") else src_root
        if not folder.is_dir():
            continue
        try:
            for p in folder.rglob("*"):
                if not p.is_file():
                    continue
                if p.suffix.lower() not in {".py", ".js", ".cjs", ".mjs", ".json"}:
                    continue
                if any(part in SKIP_DIR_NAMES for part in p.parts):
                    continue
                try:
                    paths.append(str(p.relative_to(src_root)).replace("\\", "/"))
                except ValueError:
                    continue
        except OSError:
            continue

    for key in ("runnable_scripts", "js_files", "json_files", "modules_sample"):
        for item in walk.get(key) or []:
            if isinstance(item, dict):
                rel = item.get("rel") or item.get("path") or ""
            else:
                rel = str(item)
            if rel:
                paths.append(rel.replace("\\", "/"))

    # full light pass if still thin
    if len(paths) < 50:
        for p in src_root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in {".py", ".js", ".cjs", ".mjs", ".json"}:
                continue
            if any(part in SKIP_DIR_NAMES for part in p.parts):
                continue
            try:
                paths.append(str(p.relative_to(src_root)).replace("\\", "/"))
            except ValueError:
                continue

    seen = set()
    out = []
    for p in paths:
        p = p.replace("\\", "/").lstrip("./")
        if not p or p in seen:
            continue
        seen.add(p)
        out.append(p)
    out.sort(key=lambda r: (-r.count("/"), -len(r), r))
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Bring-back plan from external accident/recovery folder")
    ap.add_argument("--src", required=True, help="External folder, e.g. D:\\from_accident")
    ap.add_argument("--dest-root", default=str(REALAI), help="RealAI-clean root")
    ap.add_argument("--apply", action="store_true", help="Copy/merge into RealAI (default plan only)")
    ap.add_argument("--min-score", type=int, default=5)
    ap.add_argument("--limit", type=int, default=400)
    args = ap.parse_args(argv)

    src = Path(args.src).resolve()
    dest_root = Path(args.dest_root).resolve()
    if not src.is_dir():
        print(f"[bring-back] missing src: {src}", file=sys.stderr)
        return 1

    out_walk = dest_root / "scan_results" / "from_accident_walk.json"
    out_walk.parent.mkdir(parents=True, exist_ok=True)
    print(f"[bring-back] deep walking {src} …")
    # Root the walker AT the external folder so depths are meaningful there
    walk = RealAIRootWalker(src, out_walk, deepen=True, start=src).run()
    print(
        f"[bring-back] walk max_depth={walk.get('max_depth_seen')} "
        f"dirs={walk.get('scanned_dirs')} nests={walk.get('nested_folder_count')} "
        f"py={walk.get('module_count')} js={walk.get('js_file_count')} "
        f"json={walk.get('json_file_count')} scripts={walk.get('runnable_script_count')}"
    )

    paths = collect_paths(src, walk)
    print(f"[bring-back] candidate files scanned={len(paths)}")

    best: Dict[str, Dict[str, Any]] = {}
    for rel in paths:
        prop = propose_into_realai(rel)
        if not prop:
            continue
        dest, reason, score = prop
        if score < args.min_score:
            continue
        src_file = src / rel
        if not src_file.is_file():
            continue
        try:
            sz = src_file.stat().st_size
        except OSError:
            continue
        if sz <= 0:
            continue
        prev = best.get(dest)
        # prefer higher score, then deeper, then larger
        depth = rel.count("/") + 1
        cand = {
            "src": str(src_file),
            "src_rel": rel,
            "dest": dest,
            "dest_abs": str(dest_root / dest),
            "reason": reason,
            "score": score,
            "depth": depth,
            "bytes": sz,
        }
        if prev is None or score > prev["score"] or (
            score == prev["score"] and (depth > prev["depth"] or sz > prev["bytes"])
        ):
            best[dest] = cand

    items = sorted(best.values(), key=lambda x: (-x["score"], -x["depth"], -x["bytes"]))
    items = items[: args.limit]

    results = []
    for it in items:
        dest_p = Path(it["dest_abs"])
        src_p = Path(it["src"])
        rec = dict(it)
        if dest_p.is_file():
            sh_s, sh_d = sha256_file(src_p), sha256_file(dest_p)
            if sh_s and sh_d and sh_s == sh_d:
                rec["action"] = "skip_same_hash"
            elif dest_p.suffix.lower() == ".json":
                rec["action"] = "would_merge" if not args.apply else "merged_json"
                if args.apply:
                    try:
                        rec["note"] = merge_json_files(src_p, dest_p)
                    except Exception as e:
                        rec["action"] = "merge_failed"
                        rec["note"] = str(e)
            elif dest_p.stat().st_size >= src_p.stat().st_size:
                rec["action"] = "skip_live_same_or_larger"
            else:
                rec["action"] = "would_copy_enrich" if not args.apply else "copied_enrich"
                if args.apply:
                    dest_p.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_p, dest_p)
        else:
            rec["action"] = "would_copy" if not args.apply else "copied"
            if args.apply:
                dest_p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_p, dest_p)
        results.append(rec)

    actions: Dict[str, int] = {}
    for r in results:
        actions[r["action"]] = actions.get(r["action"], 0) + 1

    # Highlight top finds
    top = [r for r in results if r["score"] >= 10][:40]

    payload = {
        "version": 1,
        "at": utc(),
        "src": str(src),
        "dest_root": str(dest_root),
        "apply": bool(args.apply),
        "min_score": args.min_score,
        "walk": {
            "max_depth_seen": walk.get("max_depth_seen"),
            "scanned_dirs": walk.get("scanned_dirs"),
            "nested_folder_count": walk.get("nested_folder_count"),
            "module_count": walk.get("module_count"),
            "js_file_count": walk.get("js_file_count"),
            "json_file_count": walk.get("json_file_count"),
            "deepest_nests": (walk.get("deepest_nests") or [])[:20],
            "path": str(out_walk),
        },
        "planned": len(results),
        "actions": actions,
        "top_finds": top,
        "results": results,
        "notes": [
            "Plan-only unless --apply.",
            "Sources on D: are never deleted.",
            "Dest wins on JSON key conflicts when merging.",
            "Review top_finds before applying.",
        ],
    }

    out_json = dest_root / "scan_results" / "BRING_BACK_FROM_ACCIDENT.json"
    out_md = dest_root / "scan_results" / "BRING_BACK_FROM_ACCIDENT.md"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        f"# Bring-back from `{src}` ({'APPLY' if args.apply else 'PLAN ONLY'})",
        "",
        f"- at: {payload['at']}",
        f"- walk max_depth: {walk.get('max_depth_seen')} dirs={walk.get('scanned_dirs')} nests={walk.get('nested_folder_count')}",
        f"- planned: {len(results)}",
        f"- actions: {actions}",
        "",
        "## Top finds (score >= 10)",
        "",
        "| score | depth | action | src | dest | reason |",
        "|---:|---:|---|---|---|---|",
    ]
    for r in top:
        lines.append(
            f"| {r['score']} | {r['depth']} | {r['action']} | `{r['src_rel']}` | `{r['dest']}` | {r['reason']} |"
        )
    lines += ["", "## All planned (first 60)", ""]
    for r in results[:60]:
        lines.append(
            f"- **{r['action']}** score={r['score']} `{r['src_rel']}` → `{r['dest']}` ({r['reason']})"
        )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[bring-back] planned={len(results)} actions={actions}")
    print(f"[bring-back] top_finds={len(top)}")
    print(f"[bring-back] wrote {out_json}")
    print(f"[bring-back] wrote {out_md}")
    for r in top[:15]:
        print(
            f"  [{r['score']}] {r['action']}: {r['src_rel']} → {r['dest']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
