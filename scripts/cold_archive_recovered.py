#!/usr/bin/env python3
"""
Move recovered/* dump folders to cold storage so the repo stops being a mess.

Keeps:
  - recovered/CURATED_PROMOTE_LOG.json
  - recovered/inbox/ (created empty)

Default cold root: C:\\realai-cold\\recovered-archive\\YYYYMMDD_HHMMSS

  python scripts/cold_archive_recovered.py           # move
  python scripts/cold_archive_recovered.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECOVERED = ROOT / "recovered"
KEEP_NAMES = {
    "CURATED_PROMOTE_LOG.json",
    "inbox",
    ".gitkeep",
}


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def win_or_posix_path(p: str) -> Path:
    """
    Resolve C:\\... / C:/... on Windows natively, and under WSL as /mnt/c/...
    Never create a relative 'C:' folder inside the repo (that was the mess).
    """
    s = (p or "").strip().replace("\\", "/")
    if len(s) >= 2 and s[1] == ":" and s[0].isalpha():
        drive = s[0].lower()
        rest = s[2:].lstrip("/")
        if sys.platform.startswith("win"):
            return Path(f"{drive.upper()}:/{rest}" if rest else f"{drive.upper()}:/")
        # WSL / Linux with Windows mounts
        for base in (f"/mnt/{drive}", f"/cygdrive/{drive}"):
            candidate = Path(base) / rest if rest else Path(base)
            if Path(base).exists() or base.startswith("/mnt/"):
                return candidate
        return Path(f"/mnt/{drive}") / rest if rest else Path(f"/mnt/{drive}")
    path = Path(s)
    if path.is_absolute():
        return path
    return ROOT / s


def default_cold_root() -> Path:
    env = os.environ.get("REALAI_COLD_ROOT", "").strip()
    if env:
        return win_or_posix_path(env)
    return win_or_posix_path("C:/realai-cold/recovered-archive")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--cold-root",
        default=str(default_cold_root()),
        help="Destination parent for archive (default C:\\realai-cold\\recovered-archive)",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not RECOVERED.is_dir():
        print(json.dumps({"ok": True, "moved": 0, "note": "no recovered/"}))
        return 0

    cold_root = win_or_posix_path(args.cold_root)
    cold = cold_root / utc_stamp()
    moved = []
    kept = []

    for child in sorted(RECOVERED.iterdir()):
        if child.name in KEEP_NAMES:
            kept.append(child.name)
            continue
        # keep log files at top level
        if child.is_file() and child.name.endswith(".json") and "PROMOTE" in child.name.upper():
            kept.append(child.name)
            continue
        dest = cold / child.name
        moved.append({"src": str(child), "dest": str(dest)})
        if not args.dry_run:
            cold.mkdir(parents=True, exist_ok=True)
            shutil.move(str(child), str(dest))

    if not args.dry_run:
        inbox = RECOVERED / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        (inbox / ".gitkeep").write_text("", encoding="utf-8")
        if moved:
            cold.mkdir(parents=True, exist_ok=True)
            (cold / "ARCHIVE_MANIFEST.json").write_text(
                json.dumps({"moved_at": utc_stamp(), "items": moved, "kept": kept}, indent=2),
                encoding="utf-8",
            )

    print(json.dumps({
        "ok": True,
        "dry_run": args.dry_run,
        "moved_count": len(moved),
        "kept": kept,
        "cold": str(cold) if moved else None,
        "cold_root": str(cold_root),
        "sample": moved[:10],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
