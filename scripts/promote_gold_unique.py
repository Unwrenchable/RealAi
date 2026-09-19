#!/usr/bin/env python3
"""Promote unique files from C:\\RealAI-gold into live RealAI-clean.

Only copies when the destination path is missing. Skips recovery nests,
numbered duplicates, nested realai/realai, and basenames already present
under live authority dirs.

  python scripts/promote_gold_unique.py --dry-run
  python scripts/promote_gold_unique.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

LIVE = Path(__file__).resolve().parents[1]
GOLD = Path(r"C:\RealAI-gold")
OUT_QUEUE = LIVE / "scan_results" / "gold_unique_promote_queue.json"
OUT_LOG = LIVE / "docs" / "recovery" / "2026-09-19-gold-unique-promote.json"

SKIP_PARTS = {
    "node_modules",
    ".git",
    "__pycache__",
    "dist",
    "build",
    ".venv",
    "venv",
    ".next",
    "site-packages",
    "RealAI_Recovery_SAFE",
    "repo_levels_20260830",
    "repo_levels_wiring_20260831",
    "Output",
    ".pytest_cache",
    ".vs",
    "checkpoints_lora",
}
SKIP_NAME_RE = re.compile(r" \(\d+\)\.")
OK_SUFFIX = {".py", ".ps1", ".md", ".json", ".yaml", ".yml", ".toml"}
# Prefer source/product code — never bulk-copy orphans/ nests.
CAND_ROOTS = [
    "scripts",
    "abilities",
    "agents",
    "packages",
    "providers",
    "realai",
]
REALAI_ALLOW_SUB = {
    "scanners",
    "bot",
    "plugins",
    "cli",
    "learn",
    "orchestration",
    "voice",
    "modules",
    "agents",
    "abilities",
    "config",
    "core",
    "memory",
    "training",
}
# Extra path noise inside gold/realai
SKIP_PARTS |= {
    "orphans",
    "_parked",
    "from_zips",
    "recycle_py_unique",
    "identical_twins",
    "deep_nests",
    "from_nests",
    "grok_export_realai",
    "core_unify_20260830",
    "imports",
    ".continue",
}


def skip(p: Path) -> bool:
    if any(x in p.parts for x in SKIP_PARTS):
        return True
    if SKIP_NAME_RE.search(p.name):
        return True
    if p.parts.count("realai") > 1:
        return True
    # Windows mangled dump folders / files
    if any(part.startswith("C__") or part.startswith("C_") for part in p.parts):
        return True
    if p.name.startswith("C__") or p.name.startswith("C_"):
        return True
    return False


def live_has_basename(name: str) -> Optional[Path]:
    roots = [
        LIVE / "scripts",
        LIVE / "abilities",
        LIVE / "benchmarks",
        LIVE / "realai",
        LIVE / "realai" / "scanners",
        LIVE / "packages",
        LIVE / "providers",
        LIVE / "agents",
        LIVE / "modules",
    ]
    for d in roots:
        if not d.is_dir():
            continue
        hit = d / name
        if hit.is_file():
            return hit
        try:
            for sub in d.iterdir():
                if sub.is_dir():
                    hit2 = sub / name
                    if hit2.is_file():
                        return hit2
        except OSError:
            continue
    for d in (LIVE / "scripts", LIVE / "realai" / "scanners", LIVE / "benchmarks"):
        if not d.is_dir():
            continue
        for hit in d.rglob(name):
            if hit.is_file() and "node_modules" not in hit.parts:
                return hit
    return None


def collect() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for top in CAND_ROOTS:
        root = GOLD / top
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in OK_SUFFIX:
                continue
            if skip(p):
                continue
            rel = p.relative_to(GOLD)
            parts = rel.parts
            if parts[0] == "realai":
                if len(parts) == 1:
                    continue
                if len(parts) >= 2 and parts[1] not in REALAI_ALLOW_SUB and len(parts) > 2:
                    # allow realai/*.py top-level only if clean name
                    if len(parts) != 2:
                        continue
                if len(parts) > 5:
                    continue
            dest = LIVE / rel
            if dest.is_file():
                continue
            if live_has_basename(rel.name):
                continue
            if p.suffix == ".py" and p.stat().st_size < 80:
                continue
            items.append(
                {
                    "rel": rel.as_posix(),
                    "size": p.stat().st_size,
                    "dest": dest.as_posix(),
                    "src": str(p),
                }
            )
    items.sort(key=lambda x: x["rel"])
    return items


def sha256(p: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def apply(items: List[Dict[str, Any]], dry_run: bool) -> Dict[str, Any]:
    copied: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    for it in items:
        src = Path(it["src"])
        dest = Path(it["dest"])
        if dest.exists():
            skipped.append({**it, "action": "skip_exists"})
            continue
        if dry_run:
            copied.append({**it, "action": "would_copy"})
            continue
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied.append(
                {
                    **it,
                    "action": "copied",
                    "sha256": sha256(dest),
                }
            )
        except OSError as exc:
            errors.append({**it, "action": "error", "error": str(exc)})
    return {
        "ok": not errors,
        "dry_run": dry_run,
        "source": str(GOLD),
        "dest_root": str(LIVE),
        "queued": len(items),
        "copied": len([c for c in copied if c.get("action") == "copied"]),
        "would_copy": len([c for c in copied if c.get("action") == "would_copy"]),
        "skipped": len(skipped),
        "errors": errors,
        "results": copied + skipped,
        "by_top": dict(Counter(i["rel"].split("/")[0] for i in items)),
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="Cap copies (0=all)")
    args = ap.parse_args()

    if not GOLD.is_dir():
        print(json.dumps({"ok": False, "error": f"missing {GOLD}"}))
        return 1

    items = collect()
    if args.limit and args.limit > 0:
        items = items[: args.limit]

    OUT_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    OUT_QUEUE.write_text(
        json.dumps({"source": str(GOLD), "count": len(items), "items": items}, indent=2),
        encoding="utf-8",
    )
    print(f"queue={len(items)} -> {OUT_QUEUE}")
    print("by_top", dict(Counter(i["rel"].split("/")[0] for i in items)))

    report = apply(items, dry_run=bool(args.dry_run))
    OUT_LOG.parent.mkdir(parents=True, exist_ok=True)
    OUT_LOG.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "dry_run": report["dry_run"],
                "copied": report["copied"],
                "would_copy": report["would_copy"],
                "skipped": report["skipped"],
                "errors": len(report["errors"]),
                "log": str(OUT_LOG),
            },
            indent=2,
        )
    )
    # show first 30 actions
    for r in report["results"][:30]:
        print(f"  {r.get('action')}: {r.get('rel')}")
    if len(report["results"]) > 30:
        print(f"  ... +{len(report['results']) - 30} more")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
