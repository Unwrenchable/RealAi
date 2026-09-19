#!/usr/bin/env python3
"""Apply high-score ``promote`` rows from scan_results/promote_queue.json.

- File targets (training datasets): copy into live if missing.
- Directory roots (D:): stage under recovered/from_d_roots/<name> with junk skipped.
Never overwrites existing live files unless --force.

  python scripts/promote_assemble_queue.py --dry-run
  python scripts/promote_assemble_queue.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

LIVE = Path(__file__).resolve().parents[1]
QUEUE = LIVE / "scan_results" / "promote_queue.json"
LOG = LIVE / "docs" / "recovery" / "2026-09-19-assemble-promote.json"

SKIP_DIR_NAMES: Set[str] = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".vs",
    "site-packages",
    "Output",
    ".pytest_cache",
    "checkpoints_lora",
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_file(src: Path, dest: Path, dry_run: bool, force: bool) -> Dict[str, Any]:
    rec: Dict[str, Any] = {"src": str(src), "dest": str(dest), "kind": "file"}
    if not src.is_file():
        rec.update(ok=False, action="missing_src")
        return rec
    if dest.is_file() and not force:
        same = sha256(src) == sha256(dest)
        rec.update(
            ok=True,
            action="skip_same" if same else "skip_exists",
            size=dest.stat().st_size,
        )
        return rec
    if dry_run:
        rec.update(ok=True, action="would_copy", size=src.stat().st_size)
        return rec
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    rec.update(ok=True, action="copied", size=dest.stat().st_size, sha256=sha256(dest))
    return rec


def stage_tree(src: Path, dest: Path, dry_run: bool) -> Dict[str, Any]:
    rec: Dict[str, Any] = {"src": str(src), "dest": str(dest), "kind": "tree"}
    if not src.is_dir():
        rec.update(ok=False, action="missing_src")
        return rec
    copied = 0
    skipped = 0
    errors: List[str] = []
    for p in src.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in p.parts):
            skipped += 1
            continue
        # skip huge binaries / locks
        if p.suffix.lower() in {".gguf", ".bin", ".pt", ".onnx", ".whl", ".zip", ".7z"}:
            skipped += 1
            continue
        if p.name.endswith(".lock") or p.name in {"pnpm-lock.yaml", "package-lock.json"}:
            skipped += 1
            continue
        try:
            rel = p.relative_to(src)
        except ValueError:
            continue
        target = dest / rel
        if target.exists():
            skipped += 1
            continue
        if dry_run:
            copied += 1
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
            copied += 1
        except OSError as exc:
            errors.append(f"{rel}: {exc}")
    rec.update(
        ok=not errors,
        action="would_stage" if dry_run else "staged",
        copied=copied,
        skipped=skipped,
        errors=errors[:20],
    )
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument(
        "--actions",
        default="promote",
        help="Comma list of actions to apply (default: promote)",
    )
    args = ap.parse_args()
    want = {a.strip() for a in args.actions.split(",") if a.strip()}

    data = json.loads(QUEUE.read_text(encoding="utf-8"))
    items = [i for i in (data.get("queue") or []) if i.get("action") in want]
    items.sort(key=lambda x: -int(x.get("priority") or 0))

    results: List[Dict[str, Any]] = []
    for item in items:
        src = Path(str(item.get("path") or ""))
        target_rel = str(item.get("target") or "")
        dest = LIVE / target_rel if target_rel else LIVE / "recovered" / "from_d_roots" / src.name
        base = {
            "id": item.get("id"),
            "priority": item.get("priority"),
            "subsystem": item.get("subsystem"),
            "action_requested": item.get("action"),
        }
        if src.is_file() or target_rel.endswith((".json", ".jsonl", ".py", ".md")):
            # training file rows
            if src.is_file():
                results.append({**base, **copy_file(src, dest, args.dry_run, args.force)})
            else:
                results.append({**base, "ok": False, "action": "missing_src", "src": str(src)})
        elif src.is_dir():
            results.append({**base, **stage_tree(src, dest, args.dry_run)})
        else:
            results.append({**base, "ok": False, "action": "missing_src", "src": str(src)})

    report = {
        "ok": all(r.get("ok") for r in results),
        "dry_run": bool(args.dry_run),
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "queue": str(QUEUE),
        "count": len(results),
        "copied_files": sum(1 for r in results if r.get("action") == "copied"),
        "staged_trees": sum(1 for r in results if r.get("action") == "staged"),
        "would_copy": sum(1 for r in results if r.get("action") == "would_copy"),
        "would_stage": sum(1 for r in results if r.get("action") == "would_stage"),
        "skipped": sum(1 for r in results if str(r.get("action", "")).startswith("skip")),
        "results": results,
    }
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in report if k != "results"}, indent=2))
    for r in results:
        print(
            f"  [{r.get('priority')}] {r.get('action')}  {r.get('subsystem')}  "
            f"{r.get('src')} -> {r.get('dest')}  "
            f"copied={r.get('copied', r.get('size', ''))}"
        )
    print("log", LOG)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
