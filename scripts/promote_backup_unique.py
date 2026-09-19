#!/usr/bin/env python3
"""Promote unique product code from C:\\RealAI-clean-backup into live.

Rules:
  - Copy only when destination is missing (never overwrite live).
  - Skip nests, venv, node_modules, C__ dumps, numbered ``(2)`` dups.
  - Prefer authority destinations (scripts/, realai/, abilities/, modules/, …).
  - Optional --richer: if live file exists but is a tiny stub (< live_max) and
    backup body is meaningfully larger, copy to recovered/from_backup/ and
    record a suggestion (still no overwrite unless --force-richer).

  python scripts/promote_backup_unique.py --dry-run
  python scripts/promote_backup_unique.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

LIVE = Path(__file__).resolve().parents[1]
BACKUP = Path(r"C:\RealAI-clean-backup")
OUT_QUEUE = LIVE / "scan_results" / "backup_unique_promote_queue.json"
OUT_LOG = LIVE / "docs" / "recovery" / "2026-09-19-backup-unique-promote.json"

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
    "normalized_datasets",
    "datasets",
    "logs",
    "scan_results",
    "results",
    "vendor",
    "realai.egg-info",
    "recovered",
    "media",
    "from_desktop_missing",
    "exportable",
    "historical_backups",
    "worktrees",
}
SKIP_NAME_RE = re.compile(r" \(\d+\)\.")

# Relative roots under backup to harvest
CAND_ROOTS = [
    "scripts",
    "scanners",
    "abilities",
    "agents",
    "packages",
    "providers",
    "modules",
    "core",
    "adapters",
    "tools",
    "server",
    "cli",
    "benchmarks",
    "training",
    "realai",
    "agent_tools",
    "plugins",
    "aura",
    "memory",
    "registry",
]

# Map backup top → preferred live dest top (same relative under that top)
DEST_TOP = {
    "scanners": "scripts",  # many scanners live under scripts/ in clean
    "scripts": "scripts",
    "abilities": "abilities",
    "agents": "agents",
    "packages": "packages",
    "providers": "providers",
    "modules": "modules",
    "core": "core",
    "adapters": "adapters",
    "tools": "tools",
    "server": "server",
    "cli": "cli",
    "benchmarks": "benchmarks",
    "training": "training",
    "realai": "realai",
    "agent_tools": "agent_tools",
    "plugins": "plugins",
    "aura": "aura",
    "memory": "memory",
    "registry": "registry",
}

# Root-level backup .py that belong under live/realai/ if missing
ROOT_PY_TO_REALAI = {
    "agent_runtime.py",
    "api_server.py",
    "app_framework.py",
    "audit.py",
    "bootstrap.py",
    "coding_agent.py",
    "critique.py",
    "identity.py",
    "knowledge_graph.py",
    "local_models.py",
    "local_runtime.py",
    "model_registry.py",
    "plugin_marketplace.py",
    "router.py",
    "safety.py",
    "self_improvement.py",
    "server_settings.py",
    "tools.py",
    "world_model.py",
    "realai_gui.py",
    "realai_local_server.py",
}

MIN_PY_BYTES = 120
RICHER_LIVE_MAX = 400  # treat live as stub if smaller than this
RICHER_RATIO = 2.0  # backup must be >= 2x live size


def skip(p: Path) -> bool:
    if any(x in p.parts for x in SKIP_PARTS):
        return True
    if SKIP_NAME_RE.search(p.name):
        return True
    if p.parts.count("realai") > 1:
        return True
    if any(part.startswith("C__") or part.startswith("C_") for part in p.parts):
        return True
    if p.name.startswith("C__") or p.name.startswith("C_"):
        return True
    # junk filenames from broken shells
    if p.name in {"=", "these", "PAGES"} or p.name.startswith("r'"):
        return True
    joined = "/".join(p.parts).lower()
    if any(
        tok in joined
        for tok in (
            "from_desktop",
            "_users_",
            "grok_worktrees",
            "historical_backups",
            "realai_-_copy",
            "identical_twins",
        )
    ):
        return True
    return False


def sha256(p: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def index_live_basenames() -> Dict[str, List[Path]]:
    """Basename → live paths (authority dirs only)."""
    roots = [
        LIVE / "scripts",
        LIVE / "abilities",
        LIVE / "benchmarks",
        LIVE / "realai",
        LIVE / "modules",
        LIVE / "core",
        LIVE / "packages",
        LIVE / "providers",
        LIVE / "agents",
        LIVE / "adapters",
        LIVE / "tools",
        LIVE / "server",
        LIVE / "cli",
        LIVE / "agent_tools",
        LIVE / "plugins",
        LIVE / "aura",
        LIVE / "memory",
        LIVE / "registry",
        LIVE / "training",
    ]
    idx: Dict[str, List[Path]] = defaultdict(list)
    for d in roots:
        if not d.is_dir():
            continue
        for p in d.rglob("*.py"):
            if skip(p):
                continue
            # keep depth reasonable
            try:
                rel_parts = p.relative_to(d).parts
            except ValueError:
                continue
            if len(rel_parts) > 4:
                continue
            idx[p.name].append(p)
    # also live root stubs that were moved under realai
    for name in ROOT_PY_TO_REALAI:
        for cand in (LIVE / name, LIVE / "realai" / name):
            if cand.is_file():
                idx[name].append(cand)
    return idx


def map_dest(rel: Path) -> Path:
    """Map backup-relative path to live destination."""
    parts = rel.parts
    if not parts:
        return LIVE / rel
    top = parts[0]
    if top in DEST_TOP:
        # scanners/* → scripts/* (same basename path under scripts)
        if top == "scanners":
            return LIVE / "scripts" / Path(*parts[1:])
        mapped_top = DEST_TOP[top]
        return LIVE / mapped_top / Path(*parts[1:])
    return LIVE / rel


def collect(live_idx: Dict[str, List[Path]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    missing: List[Dict[str, Any]] = []
    richer: List[Dict[str, Any]] = []

    # Root-level product py → live/realai/<name> when absent
    for name in ROOT_PY_TO_REALAI:
        src = BACKUP / name
        if not src.is_file() or skip(src):
            continue
        dest = LIVE / "realai" / name
        alt = LIVE / name
        if dest.is_file() or alt.is_file() or live_idx.get(name):
            live_paths = live_idx.get(name) or (
                [dest] if dest.is_file() else [alt] if alt.is_file() else []
            )
            for lp in live_paths:
                if not lp.is_file():
                    continue
                if (
                    lp.stat().st_size < RICHER_LIVE_MAX
                    and src.stat().st_size >= lp.stat().st_size * RICHER_RATIO
                ):
                    richer.append(
                        {
                            "rel": name,
                            "src": str(src),
                            "dest": str(lp),
                            "size_src": src.stat().st_size,
                            "size_live": lp.stat().st_size,
                            "kind": "richer",
                        }
                    )
            continue
        if src.stat().st_size < MIN_PY_BYTES:
            continue
        missing.append(
            {
                "rel": name,
                "src": str(src),
                "dest": str(dest),
                "size": src.stat().st_size,
                "kind": "missing",
            }
        )

    for top in CAND_ROOTS:
        root = BACKUP / top
        if not root.is_dir():
            continue
        for p in root.rglob("*.py"):
            if not p.is_file() or skip(p):
                continue
            try:
                rel = p.relative_to(BACKUP)
            except ValueError:
                continue
            parts = rel.parts
            if top == "realai" and len(parts) > 4:
                continue
            if top == "plugins" and len(parts) > 3:
                continue
            if p.stat().st_size < MIN_PY_BYTES:
                continue
            dest = map_dest(rel)
            # Already at exact dest?
            if dest.is_file():
                if dest.stat().st_size < RICHER_LIVE_MAX and p.stat().st_size >= dest.stat().st_size * RICHER_RATIO:
                    richer.append(
                        {
                            "rel": rel.as_posix(),
                            "src": str(p),
                            "dest": str(dest),
                            "size_src": p.stat().st_size,
                            "size_live": dest.stat().st_size,
                            "kind": "richer",
                        }
                    )
                continue
            # Basename already somewhere under authority?
            if live_idx.get(p.name):
                for lp in live_idx[p.name]:
                    if lp.stat().st_size < RICHER_LIVE_MAX and p.stat().st_size >= lp.stat().st_size * RICHER_RATIO:
                        richer.append(
                            {
                                "rel": rel.as_posix(),
                                "src": str(p),
                                "dest": str(lp),
                                "size_src": p.stat().st_size,
                                "size_live": lp.stat().st_size,
                                "kind": "richer",
                            }
                        )
                continue
            missing.append(
                {
                    "rel": rel.as_posix(),
                    "src": str(p),
                    "dest": dest.as_posix(),
                    "size": p.stat().st_size,
                    "kind": "missing",
                }
            )

    # dedupe by dest
    def _dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        out = []
        for it in sorted(items, key=lambda x: (-int(x.get("size") or x.get("size_src") or 0), x["rel"])):
            key = it["dest"]
            if key in seen:
                continue
            seen.add(key)
            out.append(it)
        return out

    return _dedupe(missing), _dedupe(richer)


def apply_missing(items: List[Dict[str, Any]], dry_run: bool) -> List[Dict[str, Any]]:
    results = []
    for it in items:
        src, dest = Path(it["src"]), Path(it["dest"])
        rec = {**it}
        if dest.exists():
            rec.update(action="skip_exists", ok=True)
        elif dry_run:
            rec.update(action="would_copy", ok=True)
        else:
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                rec.update(action="copied", ok=True, sha256=sha256(dest))
            except OSError as exc:
                rec.update(action="error", ok=False, error=str(exc))
        results.append(rec)
    return results


def apply_richer(
    items: List[Dict[str, Any]],
    dry_run: bool,
    force: bool,
) -> List[Dict[str, Any]]:
    """Copy richer bodies beside live under recovered/from_backup/ or force overwrite."""
    results = []
    staging = LIVE / "recovered" / "from_backup"
    for it in items:
        src, dest = Path(it["src"]), Path(it["dest"])
        rec = {**it}
        if force:
            target = dest
            mode = "overwrite_live"
        else:
            # stage next to original relative path under recovered/from_backup
            try:
                rel = dest.relative_to(LIVE)
            except ValueError:
                rel = Path(dest.name)
            target = staging / rel
            mode = "stage"
        if dry_run:
            rec.update(action=f"would_{mode}", ok=True, target=str(target))
        else:
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target)
                rec.update(action=mode, ok=True, target=str(target), sha256=sha256(target))
            except OSError as exc:
                rec.update(action="error", ok=False, error=str(exc))
        results.append(rec)
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--richer", action="store_true", help="Also stage richer-than-stub backups")
    ap.add_argument("--force-richer", action="store_true", help="Overwrite live stubs with richer backup bodies")
    args = ap.parse_args()

    if not BACKUP.is_dir():
        print(json.dumps({"ok": False, "error": f"missing {BACKUP}"}))
        return 1

    live_idx = index_live_basenames()
    missing, richer = collect(live_idx)
    if args.limit and args.limit > 0:
        missing = missing[: args.limit]

    OUT_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    OUT_QUEUE.write_text(
        json.dumps(
            {
                "source": str(BACKUP),
                "missing_count": len(missing),
                "richer_count": len(richer),
                "missing": missing,
                "richer": richer[:200],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"missing={len(missing)} richer={len(richer)} queue->{OUT_QUEUE}")
    print("missing_by_top", dict(Counter((m["rel"].split("/")[0] if "/" in m["rel"] else "_root") for m in missing)))

    results = apply_missing(missing, dry_run=bool(args.dry_run))
    richer_results: List[Dict[str, Any]] = []
    if args.richer or args.force_richer:
        richer_results = apply_richer(richer, dry_run=bool(args.dry_run), force=bool(args.force_richer))

    report = {
        "ok": all(r.get("ok") for r in results + richer_results),
        "dry_run": bool(args.dry_run),
        "source": str(BACKUP),
        "dest_root": str(LIVE),
        "copied": sum(1 for r in results if r.get("action") == "copied"),
        "would_copy": sum(1 for r in results if r.get("action") == "would_copy"),
        "skipped": sum(1 for r in results if r.get("action") == "skip_exists"),
        "richer_staged": sum(1 for r in richer_results if r.get("action") in ("stage", "would_stage")),
        "richer_overwritten": sum(1 for r in richer_results if r.get("action") in ("overwrite_live", "would_overwrite_live")),
        "errors": [r for r in results + richer_results if not r.get("ok")],
        "results": results,
        "richer_results": richer_results[:100],
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }
    OUT_LOG.parent.mkdir(parents=True, exist_ok=True)
    OUT_LOG.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "dry_run": report["dry_run"],
                "copied": report["copied"],
                "would_copy": report["would_copy"],
                "richer_staged": report["richer_staged"],
                "richer_overwritten": report["richer_overwritten"],
                "errors": len(report["errors"]),
                "log": str(OUT_LOG),
            },
            indent=2,
        )
    )
    for r in results[:40]:
        print(f"  {r.get('action')}: {r.get('rel')} ({r.get('size')} B) -> {r.get('dest')}")
    if len(results) > 40:
        print(f"  ... +{len(results) - 40} more")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
