#!/usr/bin/env python3
"""
Index C:\\RealAI-clean\\_quarantine for self-improve / promote / dispatcher.

Goal: let the Hive learn from quarantine the same way it hunts lost/unique code —
surface candidates that are NOT already live under abilities/, agents/, realai/, scripts/.

Does NOT run quarantine code. Writes:
  scan_results/quarantine_catalog.json
  scan_results/quarantine_promote_candidates.json
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

def _product_root() -> Path:
    """Prefer workspace that contains _quarantine (not package realai/)."""
    for key in ("REALAI_WORKSPACE", "REALAI_ROOT", "REALAI_HOME"):
        raw = (os.environ.get(key) or "").strip()
        if not raw:
            continue
        p = Path(raw)
        if (p / "_quarantine").is_dir():
            return p
        if p.name.lower() == "realai" and (p.parent / "_quarantine").is_dir():
            return p.parent
    here = Path(__file__).resolve().parents[1]  # …/scripts → workspace
    if (here / "_quarantine").is_dir():
        return here
    try:
        from realai.workspace import product_root

        return product_root()
    except Exception:
        return here


ROOT = _product_root()
QUAR = ROOT / "_quarantine"
OUT_DIR = ROOT / "scan_results"
CATALOG = OUT_DIR / "quarantine_catalog.json"
CANDIDATES = OUT_DIR / "quarantine_promote_candidates.json"

LIVE_ROOTS = (
    "abilities",
    "agents",
    "agent_tools",
    "modules",
    "realai",
    "scripts",
    "plugins",
    "world_model",
    "config",
)

SKIP_DIR = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "site-packages",
    "checkpoints_lora",
    "clean_backup_20260708_041701",
    "clean_backup_20260708_112400",
    "clean_backup_20260708_112721",
    "clean_backup_20260708_113054",
    ".kilo",
    "worktrees",
}

SKIP_NAME_PREFIXES = ("C__", "C_Users_", "_Users_", "Users_tsmit_")
SKIP_REL_CONTAINS = (
    "clean_backup_",
    "og_mess",
    "kilo_worktrees",
    "cotton-mistake",
    "HOMEPC",
    "from-wsl",
    "from-zips",
    "from-accident",
)

KEYWORDS = (
    "self_improve",
    "self_heal",
    "selfheal",
    "orchestr",
    "agent_runtime",
    "world_model",
    "aura_memory",
    "hive",
    "dispatcher",
    "promote",
    "ability",
    "plugin",
    "provider",
    "router",
    "guardian",
    "overseer",
    "multi_agent",
    "vulkan",
    "llama",
    "embeddings",
    "organ",
    "rackup",
    "secure_tool",
    "device_selector",
)

MAX_DEPTH = int(os.environ.get("REALAI_QUAR_MAX_DEPTH") or "5")
MAX_FILES = int(os.environ.get("REALAI_QUAR_MAX_FILES") or "8000")


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def score(name: str, rel: str) -> int:
    blob = f"{name} {rel}".lower()
    s = 0
    for k in KEYWORDS:
        if k in blob:
            s += 3
    if name.endswith(".py"):
        s += 1
    if name in ("__init__.py", "setup.py", "conftest.py"):
        s -= 2
    # Prefer non-nested recycle noise
    if "clean_backup" in rel or "HOMEPC" in rel or "from-wsl" in rel:
        s -= 1
    return s


def live_basenames() -> Set[str]:
    names: Set[str] = set()
    for root_name in LIVE_ROOTS:
        base = ROOT / root_name
        if not base.is_dir():
            continue
        for p in base.rglob("*.py"):
            if any(part in SKIP_DIR for part in p.parts):
                continue
            names.add(p.name.lower())
            # also stem for fuzzy unique
            names.add(p.stem.lower())
    return names


def file_fingerprint(path: Path, limit: int = 65536) -> str:
    h = hashlib.sha1()
    try:
        with path.open("rb") as f:
            h.update(f.read(limit))
    except OSError:
        return ""
    return h.hexdigest()[:16]


def walk_quarantine() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not QUAR.is_dir():
        return [], {"error": f"missing {QUAR}"}

    live = live_basenames()
    rows: List[Dict[str, Any]] = []
    top_dirs = [p for p in QUAR.iterdir() if p.is_dir() and p.name not in SKIP_DIR and not p.name.startswith(".")]
    stats = {
        "quarantine": str(QUAR),
        "top_dirs": len(top_dirs),
        "scanned_files": 0,
        "unique_name_count": 0,
        "keyword_hits": 0,
        "max_depth": MAX_DEPTH,
        "capped": False,
    }

    for top in sorted(top_dirs, key=lambda p: p.name.lower()):
        for dirpath, dirnames, filenames in os.walk(top):
            rel_dir = Path(dirpath).relative_to(QUAR)
            depth = len(rel_dir.parts)
            dirnames[:] = [
                d
                for d in dirnames
                if d not in SKIP_DIR and not d.startswith(".") and depth < MAX_DEPTH
            ]
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                stats["scanned_files"] += 1
                if stats["scanned_files"] > MAX_FILES:
                    stats["capped"] = True
                    return rows, stats
                path = Path(dirpath) / fn
                if fn.startswith(SKIP_NAME_PREFIXES):
                    continue
                try:
                    rel = str(path.relative_to(ROOT)).replace("\\", "/")
                except ValueError:
                    rel = str(path)
                if any(tok in rel for tok in SKIP_REL_CONTAINS):
                    continue
                sc = score(fn, rel)
                unique = fn.lower() not in live and Path(fn).stem.lower() not in live
                if sc >= 3:
                    stats["keyword_hits"] += 1
                if unique:
                    stats["unique_name_count"] += 1
                if sc < 3 and not unique:
                    continue
                rows.append(
                    {
                        "name": fn,
                        "rel": rel,
                        "top": top.name,
                        "score": sc,
                        "unique_name": unique,
                        "size": path.stat().st_size if path.is_file() else 0,
                        "sha1_16": file_fingerprint(path),
                        "suggest": (
                            "promote_review"
                            if unique and sc >= 3
                            else "unique_name"
                            if unique
                            else "keyword_overlap"
                        ),
                    }
                )
    rows.sort(key=lambda r: (-r["score"], -int(r["unique_name"]), r["rel"]))
    return rows, stats


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows, stats = walk_quarantine()
    promote = [r for r in rows if r.get("suggest") == "promote_review"][:200]
    catalog = {
        "generated_at": utc(),
        "root": str(ROOT),
        "stats": stats,
        "count": len(rows),
        "entries": rows[:2000],
        "promote_candidates_count": len(promote),
    }
    CATALOG.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    CANDIDATES.write_text(
        json.dumps(
            {
                "generated_at": utc(),
                "count": len(promote),
                "note": "Unique+keyword hits from _quarantine for human/self-heal promote review",
                "candidates": promote,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[quarantine] scanned={stats.get('scanned_files')} entries={len(rows)} promote={len(promote)}")
    print(f"[quarantine] wrote {CATALOG}")
    print(f"[quarantine] wrote {CANDIDATES}")
    if promote:
        print("[quarantine] top promote candidates:")
        for c in promote[:15]:
            print(f"  {c['score']:2d}  {c['rel']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
