#!/usr/bin/env python3
"""Wire staged D: roots into correctly named live RealAI locations.

Mapping (RealAI names, not random dump folders):
  recovered/from_d_roots/realai-cli      -> packages/cli          (unique command files)
  recovered/from_d_roots/realai-sdk-js   -> packages/realai-sdk   (API SDK; not game sdk-ts)
  recovered/from_d_roots/tools_realai    -> tools/realai
  recovered/from_d_roots/realai/*.py     -> modules/desktop_unique or realai/ (unique only)

Never overwrites existing live files. Skips junk (.db, locks, node_modules).

  python scripts/wire_staged_d_roots.py --dry-run
  python scripts/wire_staged_d_roots.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

LIVE = Path(__file__).resolve().parents[1]
STAGED = LIVE / "recovered" / "from_d_roots"
LOG = LIVE / "docs" / "recovery" / "2026-09-19-wire-staged-d-roots.json"

SKIP_NAMES = {".ds_store", "thumbs.db", "pnpm-lock.yaml", "package-lock.json"}
SKIP_SUFFIX = {".db", ".sqlite", ".sqlite3", ".gguf", ".bin", ".pt", ".onnx", ".zip", ".7z"}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_unique(src: Path, dest: Path, dry_run: bool) -> Dict[str, Any]:
    rec: Dict[str, Any] = {"src": str(src), "dest": str(dest)}
    if not src.is_file():
        rec.update(ok=False, action="missing_src")
        return rec
    if src.name.lower() in SKIP_NAMES or src.suffix.lower() in SKIP_SUFFIX:
        rec.update(ok=True, action="skip_junk")
        return rec
    if dest.exists():
        same = False
        try:
            same = sha256(src) == sha256(dest)
        except OSError:
            pass
        rec.update(ok=True, action="skip_same" if same else "skip_exists", size=dest.stat().st_size)
        return rec
    if dry_run:
        rec.update(ok=True, action="would_copy", size=src.stat().st_size)
        return rec
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    rec.update(ok=True, action="copied", size=dest.stat().st_size)
    return rec


def wire_tree(src_root: Path, dest_root: Path, dry_run: bool, *, only_suffix: Optional[set] = None) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not src_root.is_dir():
        return [{"ok": False, "action": "missing_src", "src": str(src_root), "dest": str(dest_root)}]
    for p in src_root.rglob("*"):
        if not p.is_file():
            continue
        if only_suffix and p.suffix.lower() not in only_suffix:
            continue
        rel = p.relative_to(src_root)
        out.append(copy_unique(p, dest_root / rel, dry_run))
    return out


def wire_cli(dry_run: bool) -> List[Dict[str, Any]]:
    """Unique CLI pieces into packages/cli (existing RealAI CLI package)."""
    src = STAGED / "realai-cli"
    dest = LIVE / "packages" / "cli"
    results = []
    # Prefer unique command modules + config; do not clobber richer live index.ts
    for rel in (
        "src/config.ts",
        "src/commands/chat.ts",
        "src/commands/login.ts",
        "src/commands/models.ts",
        "src/commands/whoami.ts",
    ):
        results.append(copy_unique(src / rel, dest / rel, dry_run))
    # If package.json missing name @realai/cli, leave live alone (skip_exists)
    results.append(copy_unique(src / "package.json", dest / "package.json", dry_run))
    return results


def wire_sdk(dry_run: bool) -> List[Dict[str, Any]]:
    """API SDK -> packages/realai-sdk (do not dump into game packages/sdk-ts)."""
    return wire_tree(
        STAGED / "realai-sdk-js",
        LIVE / "packages" / "realai-sdk",
        dry_run,
        only_suffix={".ts", ".json", ".md"},
    )


def wire_tools(dry_run: bool) -> List[Dict[str, Any]]:
    """MCP/tools launchers -> tools/realai/."""
    return wire_tree(STAGED / "tools_realai", LIVE / "tools" / "realai", dry_run)


def wire_desktop_lambdas(dry_run: bool) -> List[Dict[str, Any]]:
    """Unique lambda modules from staged D:/realai into modules/desktop_unique."""
    src_root = STAGED / "realai"
    dest_root = LIVE / "modules" / "desktop_unique"
    results = []
    if not src_root.is_dir():
        return results
    for p in src_root.glob("lambda_*.py"):
        results.append(copy_unique(p, dest_root / p.name, dry_run))
    # local_model_cli is product-related
    for name in ("local_model_cli.py", "standalone_ai.py"):
        p = src_root / name
        if p.is_file():
            results.append(copy_unique(p, dest_root / name, dry_run))
    return results


def sanitize_realai_name(raw: str) -> str:
    """Turn arbitrary D: folder names into realai_* identifiers."""
    s = raw.strip().replace("\\", "/").rstrip("/")
    base = s.split("/")[-1]
    base = base.replace(" - Copy", "_copy").replace("- Copy", "_copy")
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base)
    base = base.replace("-", "_")
    base = re.sub(r"_+", "_", base).strip("._").lower()
    if not base:
        base = "realai_root"
    if not base.startswith("realai"):
        base = f"realai_{base}"
    return base


def stage_needs_review(dry_run: bool) -> List[Dict[str, Any]]:
    """Stage needs_review D: roots under recovered/from_d_roots/realai_* names."""
    queue = json.loads((LIVE / "scan_results" / "promote_queue.json").read_text(encoding="utf-8"))
    items = [i for i in (queue.get("queue") or []) if i.get("action") == "needs_review"]
    results: List[Dict[str, Any]] = []
    SKIP_DIR = {
        "node_modules",
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        ".next",
        "site-packages",
        "Output",
        "checkpoints_lora",
    }
    for item in sorted(items, key=lambda x: -int(x.get("priority") or 0)):
        raw_path = str(item.get("path") or "")
        # Fix broken path with space: "D:/recovered /atomicfizzcaps-live/api"
        candidates = [
            Path(raw_path),
            Path(raw_path.replace("recovered /", "recovered/")),
            Path(raw_path.replace("D:/recovered /", "D:/from_accident/")),
        ]
        src = next((c for c in candidates if c.exists()), candidates[0])
        name = sanitize_realai_name(src.name if src.name else str(item.get("id")))
        # special cases for clearer RealAI names
        low = str(src).lower().replace("\\", "/")
        if "atomicfizzcaps-live/api" in low or low.endswith("/api") and "atomicfizz" in low:
            name = "realai_api_atomicfizz"
        elif "design-system" in low:
            name = "realai_design_system"
        elif "orchestration" in low:
            name = "realai_orchestration"
        elif name == "realai_archive":
            name = "realai_archive"
        elif "historical" in low:
            name = "realai_historical_backups"
        dest = STAGED / name
        rec: Dict[str, Any] = {
            "id": item.get("id"),
            "priority": item.get("priority"),
            "subsystem": item.get("subsystem"),
            "src": str(src),
            "dest": str(dest),
            "kind": "needs_review_stage",
        }
        if not src.exists():
            rec.update(ok=False, action="missing_src")
            results.append(rec)
            continue
        if src.is_file():
            results.append({**rec, **copy_unique(src, dest, dry_run)})
            continue
        copied = skipped = 0
        errors: List[str] = []
        max_files = 1500
        for p in src.rglob("*"):
            if copied >= max_files:
                rec["truncated"] = True
                break
            if not p.is_file():
                continue
            if any(part in SKIP_DIR for part in p.parts):
                skipped += 1
                continue
            if p.suffix.lower() in SKIP_SUFFIX or p.name.lower() in SKIP_NAMES:
                skipped += 1
                continue
            # cap huge trees somewhat: skip media-heavy
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".wav", ".mp3"}:
                skipped += 1
                continue
            try:
                rel = p.relative_to(src)
            except ValueError:
                continue
            # keep shallow for archive dumps
            if len(rel.parts) > 6:
                skipped += 1
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
            errors=errors[:15],
        )
        results.append(rec)
    return results


def wire_design_system(dry_run: bool) -> List[Dict[str, Any]]:
    """If staged design system exists, wire unique files into packages/design-system."""
    src = STAGED / "realai_design_system"
    dest = LIVE / "packages" / "design-system"
    if not src.is_dir():
        return []
    return wire_tree(src, dest, dry_run, only_suffix={".ts", ".tsx", ".js", ".jsx", ".css", ".json", ".md"})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-needs-review", action="store_true")
    args = ap.parse_args()

    results: List[Dict[str, Any]] = []
    sections: Dict[str, List[Dict[str, Any]]] = {
        "cli": wire_cli(args.dry_run),
        "sdk": wire_sdk(args.dry_run),
        "tools": wire_tools(args.dry_run),
        "desktop_unique": wire_desktop_lambdas(args.dry_run),
    }
    for name, rows in sections.items():
        for r in rows:
            r["section"] = name
            results.append(r)

    needs_review_rows: List[Dict[str, Any]] = []
    if not args.skip_needs_review:
        needs_review_rows = stage_needs_review(args.dry_run)
        for r in needs_review_rows:
            r["section"] = "needs_review"
            results.append(r)
        # after staging, try design-system wire
        for r in wire_design_system(args.dry_run):
            r["section"] = "design_system"
            results.append(r)

    report = {
        "ok": all(r.get("ok", True) for r in results),
        "dry_run": bool(args.dry_run),
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "copied": sum(1 for r in results if r.get("action") == "copied"),
        "would_copy": sum(1 for r in results if r.get("action") == "would_copy"),
        "staged": sum(1 for r in results if r.get("action") == "staged"),
        "would_stage": sum(1 for r in results if r.get("action") == "would_stage"),
        "skipped": sum(1 for r in results if str(r.get("action", "")).startswith("skip")),
        "mapping": {
            "realai-cli": "packages/cli (unique commands/config)",
            "realai-sdk-js": "packages/realai-sdk",
            "tools_realai": "tools/realai",
            "lambda_*.py": "modules/desktop_unique",
            "needs_review": "recovered/from_d_roots/realai_* then selective wire",
        },
        "results": results,
    }
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {k: report[k] for k in report if k != "results"},
            indent=2,
        )
    )
    for r in results:
        if r.get("action") in {"copied", "would_copy", "staged", "would_stage", "missing_src"}:
            print(
                f"  [{r.get('section')}] {r.get('action')}  "
                f"{r.get('src')} -> {r.get('dest')}  "
                f"{r.get('copied', r.get('size', ''))}"
            )
    print("log", LOG)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
