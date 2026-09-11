#!/usr/bin/env python3
"""
Diff imports/external snapshots vs living RealAI-clean trees.

Writes:
  scan_results/promote_allowlist_from_imports.json

Policy:
  - Snapshots under imports/external remain the bulk store for archives.
  - Multi-GB external roots (D:\\realai_archives, giant_hold) stay EXTRA_READ only.
  - Allowlist only proposes *source* files that look novel (basename or content)
    and small enough to promote into living paths.

Usage:
  python scripts/diff_imports_promote_allowlist.py
  python scripts/diff_imports_promote_allowlist.py --apply-hints  # also print curated_promote stub
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
IMPORTS = ROOT / "imports" / "external"
OUT = ROOT / "scan_results" / "promote_allowlist_from_imports.json"

LIVING = [
    ROOT / "realai",
    ROOT / "core",
    ROOT / "modules",
    ROOT / "agents",
    ROOT / "apps",
    ROOT / "plugins",
    ROOT / "packages",
    ROOT / "agent_tools",
    ROOT / "adapters",
    ROOT / "server",
]

SKIP_DIRS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    ".next",
    "out",
}
SRC_EXT = {".py", ".ts", ".tsx", ".js", ".mjs", ".json", ".yaml", ".yml", ".md", ".toml"}
MAX_BYTES = 1_500_000


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(p: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def iter_src(root: Path):
    if not root.exists():
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix.lower() not in SRC_EXT:
                continue
            try:
                if p.stat().st_size > MAX_BYTES:
                    continue
            except OSError:
                continue
            yield p


def living_index() -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    """basename -> paths; sha -> path"""
    by_name: Dict[str, List[str]] = {}
    by_hash: Dict[str, str] = {}
    for root in LIVING:
        for p in iter_src(root):
            by_name.setdefault(p.name, []).append(str(p.relative_to(ROOT)).replace("\\", "/"))
            h = sha256(p)
            if h:
                by_hash[h] = str(p.relative_to(ROOT)).replace("\\", "/")
    return by_name, by_hash


def suggest_dest(src_rel: str, basename: str) -> str:
    """Heuristic living destination for a snapshot file."""
    s = src_rel.replace("\\", "/")
    if "agent_tools_gold" in s or s.startswith("imports/external/agent_tools"):
        return f"agent_tools/{basename}" if basename != "__init__.py" else "agent_tools/__init__.py"
    if "/tooling/" in s:
        return f"agent_tools/tooling/{basename}"
    if "/providers/" in s:
        return f"agent_tools/providers/{basename}"
    if "/engine/" in s:
        return f"agent_tools/engine/{basename}"
    if "recovery_packages/sdk-ts" in s:
        return f"packages/sdk-ts/src/{basename}"
    if "C_realai_modules/" in s:
        rest = s.split("C_realai_modules/", 1)[-1]
        return f"modules/{rest}"
    if "C_realai_plugins/" in s:
        rest = s.split("C_realai_plugins/", 1)[-1]
        return f"plugins/{rest}"
    if "C_realai_server/" in s:
        rest = s.split("C_realai_server/", 1)[-1]
        return f"server/{rest}"
    if "grok_export_realai/" in s:
        rest = s.split("grok_export_realai/", 1)[-1]
        return f"realai/{rest}"
    if "recovery_agents/" in s:
        rest = s.split("recovery_agents/", 1)[-1]
        return f"agents/{rest}"
    if "unique-modules/" in s:
        rest = s.split("unique-modules/", 1)[-1]
        return f"imports/promoted/{rest}"
    return f"imports/promoted/{basename}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply-hints", action="store_true")
    args = ap.parse_args()

    by_name, by_hash = living_index()
    items: List[Dict[str, Any]] = []
    stats = {
        "snapshot_files": 0,
        "identical_hash": 0,
        "same_name_diff_hash": 0,
        "novel_basename": 0,
        "skipped": 0,
    }

    if not IMPORTS.is_dir():
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({"error": "no imports/external", "utc": utc()}, indent=2))
        print(f"No {IMPORTS}")
        return 1

    for p in iter_src(IMPORTS):
        stats["snapshot_files"] += 1
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        h = sha256(p)
        if h and h in by_hash:
            stats["identical_hash"] += 1
            continue
        names = by_name.get(p.name) or []
        if names and h:
            stats["same_name_diff_hash"] += 1
            kind = "newer_or_fork"
        elif not names:
            stats["novel_basename"] += 1
            kind = "novel"
        else:
            kind = "name_collision"
        dest = suggest_dest(rel, p.name)
        # Don't propose clobbering living agent_tools if already promoted identical structure
        living_dest = ROOT / dest
        mode = "if_missing"
        if living_dest.is_file():
            if h and sha256(living_dest) == h:
                stats["identical_hash"] += 1
                continue
            mode = "review_diff"
        items.append(
            {
                "id": f"imp_{len(items):04d}_{p.stem}"[:64],
                "kind": kind,
                "src": rel,
                "dest": dest,
                "mode": mode,
                "bytes": p.stat().st_size,
                "sha256": h,
                "living_same_name": names[:5],
            }
        )

    # Prioritize gold + novel
    priority = []
    rest = []
    for it in items:
        if "agent_tools" in it["src"] or it["kind"] == "novel":
            priority.append(it)
        else:
            rest.append(it)
    ordered = priority + rest

    report = {
        "utc": utc(),
        "policy": {
            "snapshots_stay": "imports/external/**",
            "extra_read_only_roots": [
                r"D:\realai_archives",
                r"C:\realai_giant_hold",
                r"C:\RealAI_Recovery_SAFE",
            ],
            "promote_via": "scripts/curated_promote.py or manual copy",
            "already_living_gold": "agent_tools/ + realai/agent_tools_gold/",
        },
        "stats": stats,
        "candidates": ordered[:500],
        "candidate_count": len(ordered),
        "curated_promote_stub": [
            {
                "id": c["id"],
                "src": c["src"],
                "dest": c["dest"],
                "mode": "if_missing_or_smaller" if c["mode"] == "if_missing" else "keep_live",
            }
            for c in ordered[:80]
            if c["kind"] in ("novel", "newer_or_fork") and "agent_tools" not in c["dest"]
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"stats": stats, "candidates": len(ordered), "out": str(OUT)}, indent=2))
    if args.apply_hints:
        print("\n# curated_promote stub (first 20 novel/non-gold):")
        for c in report["curated_promote_stub"][:20]:
            print(f"  {c['src']} -> {c['dest']} ({c['mode']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
