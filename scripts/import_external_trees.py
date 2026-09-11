#!/usr/bin/env python3
"""
Host-side external import for RealAI-clean.

Product-mode craft tools are locked to REALAI_WORKSPACE via safe_under.
Optional runtime reads of sibling trees require REALAI_EXTRA_READ_ROOTS
(read-only). This script does not rely on that — it copies curated trees
*into* RealAI-clean so product mode can always see them.

Usage:
  python scripts/import_external_trees.py                 # dry-run inventory
  python scripts/import_external_trees.py --apply         # copy allowlisted items
  python scripts/import_external_trees.py --apply --force
  python scripts/import_external_trees.py --id agent_tools_gold --apply

Imports land under imports/external/<id>/ (snapshots) unless dest is a living path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "recovered" / "EXTERNAL_IMPORT_LOG.json"
EXCLUDE_ALWAYS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", ".pytest_cache", ".next"}

# Curated allowlist — prefer small gold over multi-GB dumps.
IMPORTS: List[Dict[str, Any]] = [
    # --- living (careful) ---
    {
        "id": "vscode_extension_live",
        "src": r"C:\Users\tsmit\realai\apps\vscode",
        "dest": "apps/vscode",
        "kind": "dir",
        "exclude_dirs": EXCLUDE_ALWAYS,
        "notes": "VS Code extension sources. skip_if_dest_has preserves reconstructed activate().",
        "skip_if_dest_has": ["src/extension.ts"],
        "optional": True,
    },
    {
        "id": "fusion_ui",
        "src": r"C:\Users\tsmit\realai\fusion-ui",
        "dest": "apps/fusion-ui",
        "kind": "dir",
        "notes": "Legacy static Fusion UI.",
        "optional": True,
    },
    {
        "id": "realai_documents",
        "src": r"C:\Users\tsmit\realai_documents",
        "dest": "docs/external_contracts",
        "kind": "dir",
        "glob": "*.md",
        "notes": "RackUp/ROC contracts (not UI mockups).",
        "optional": True,
    },
    # --- gold snapshots under imports/external ---
    {
        "id": "agent_tools_gold",
        "src": r"C:\realai_recovery_\agent_tools_gold",
        "dest": "imports/external/agent_tools_gold",
        "kind": "dir",
        "notes": "Best agent-tools package (providers, tooling, engine, registry).",
    },
    {
        "id": "unique_modules",
        "src": r"C:\realai_recovery_\unique-modules",
        "dest": "imports/external/unique-modules",
        "kind": "dir",
        "notes": "Unique modules + gold scanners from recovery tree.",
    },
    {
        "id": "recovery_agents",
        "src": r"C:\realai_recovery_\agents",
        "dest": "imports/external/recovery_agents",
        "kind": "dir",
        "notes": "Agents tree from C:\\realai_recovery_.",
        "optional": True,
    },
    {
        "id": "recovery_plugins",
        "src": r"C:\realai_recovery_\plugins",
        "dest": "imports/external/recovery_plugins",
        "kind": "dir",
        "notes": "Plugins snapshot from recovery.",
        "optional": True,
    },
    {
        "id": "recovery_packages",
        "src": r"C:\realai_recovery_\packages",
        "dest": "imports/external/recovery_packages",
        "kind": "dir",
        "notes": "packages/ including sdk-ts game/bridge clients.",
        "optional": True,
    },
    {
        "id": "recovery_training",
        "src": r"C:\realai_recovery_\training",
        "dest": "imports/external/recovery_training",
        "kind": "dir",
        "notes": "Training snapshots from recovery.",
        "optional": True,
    },
    {
        "id": "C_realai_modules",
        "src": r"C:\realai\modules",
        "dest": "imports/external/C_realai_modules",
        "kind": "dir",
        "notes": "Living-ish modules tree from C:\\realai.",
        "optional": True,
    },
    {
        "id": "C_realai_plugins",
        "src": r"C:\realai\plugins",
        "dest": "imports/external/C_realai_plugins",
        "kind": "dir",
        "notes": "Plugins from C:\\realai.",
        "optional": True,
    },
    {
        "id": "C_realai_server",
        "src": r"C:\realai\server",
        "dest": "imports/external/C_realai_server",
        "kind": "dir",
        "notes": "Server package from C:\\realai.",
        "optional": True,
    },
    {
        "id": "grok_export_realai",
        "src": r"C:\realai_grok_export\realai",
        "dest": "imports/external/grok_export_realai",
        "kind": "dir",
        "notes": "Grok export realai package snapshot.",
        "optional": True,
    },
    {
        "id": "vscode_snapshot_users",
        "src": r"C:\Users\tsmit\realai\apps\vscode",
        "dest": "imports/external/vscode_snapshot_users_realai",
        "kind": "dir",
        "notes": "Raw vscode snapshot (may have corrupted extension.ts).",
        "optional": True,
    },
    {
        "id": "vscode_snapshot_recovery",
        "src": r"C:\realai_recovery_\apps\vscode",
        "dest": "imports/external/vscode_snapshot_recovery",
        "kind": "dir",
        "notes": "VS Code snapshot from recovery tree.",
        "optional": True,
    },
    # --- probe-only / often empty ---
    {
        "id": "realai_good_probe",
        "src": r"C:\Users\tsmit\realai_good",
        "dest": "imports/external/realai_good",
        "kind": "dir",
        "notes": "Often empty shell; probe only.",
        "optional": True,
    },
    {
        "id": "RealAi_unified_probe",
        "src": r"C:\RealAi-unified",
        "dest": "imports/external/RealAi_unified_probe",
        "kind": "dir",
        "exclude_dirs": EXCLUDE_ALWAYS | {"node_modules", ".venv"},
        "notes": "Unified attempt — many dirs empty; probe shallow files only via robocopy-style copy.",
        "optional": True,
        "max_files": 200,
    },
]


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(p: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def should_skip_dir(name: str, exclude: set) -> bool:
    return name in exclude


def copy_tree(
    src: Path,
    dest: Path,
    *,
    force: bool,
    exclude_dirs: set,
    glob: Optional[str] = None,
    max_files: Optional[int] = None,
) -> Dict[str, int]:
    stats = {"copied": 0, "skipped": 0, "updated": 0}
    if not src.exists():
        return stats

    if src.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_file() and not force and sha256_file(src) == sha256_file(dest):
            stats["skipped"] += 1
            return stats
        shutil.copy2(src, dest)
        stats["copied"] += 1
        return stats

    if glob:
        dest.mkdir(parents=True, exist_ok=True)
        for p in src.glob(glob):
            if not p.is_file():
                continue
            d = dest / p.name
            if d.is_file() and not force and sha256_file(p) == sha256_file(d):
                stats["skipped"] += 1
                continue
            shutil.copy2(p, d)
            stats["copied"] += 1
        return stats

    for p in src.rglob("*"):
        if max_files is not None and (stats["copied"] + stats["updated"]) >= max_files:
            break
        if p.is_dir():
            continue
        rel_parts = p.relative_to(src).parts
        if any(should_skip_dir(part, exclude_dirs) for part in rel_parts[:-1]):
            continue
        # skip huge binaries by extension
        if p.suffix.lower() in {".gguf", ".bin", ".pt", ".onnx", ".zip", ".7z", ".tar", ".gz"}:
            stats["skipped"] += 1
            continue
        try:
            if p.stat().st_size > 25 * 1024 * 1024:
                stats["skipped"] += 1
                continue
        except OSError:
            continue
        d = dest / Path(*rel_parts)
        d.parent.mkdir(parents=True, exist_ok=True)
        if d.is_file() and not force:
            if sha256_file(p) == sha256_file(d):
                stats["skipped"] += 1
                continue
        action = "updated" if d.is_file() else "copied"
        try:
            shutil.copy2(p, d)
            stats[action] += 1
        except OSError:
            stats["skipped"] += 1
    return stats


def inventory_item(item: Dict[str, Any]) -> Dict[str, Any]:
    src = Path(item["src"])
    dest = ROOT / item["dest"]
    rec: Dict[str, Any] = {
        "id": item["id"],
        "src": str(src),
        "dest": str(dest),
        "src_exists": src.exists(),
        "dest_exists": dest.exists(),
        "notes": item.get("notes"),
        "optional": bool(item.get("optional")),
    }
    if src.exists():
        if src.is_dir():
            files = [
                p
                for p in src.rglob("*")
                if p.is_file()
                and not any(
                    x in p.parts for x in (item.get("exclude_dirs") or EXCLUDE_ALWAYS)
                )
            ]
            # cap listing cost
            files = files[:5000]
            rec["src_files"] = len(files)
            rec["src_bytes"] = sum(p.stat().st_size for p in files if p.exists())
        else:
            rec["src_files"] = 1
            rec["src_bytes"] = src.stat().st_size
    else:
        rec["src_files"] = 0
        rec["src_bytes"] = 0
    return rec


def apply_item(item: Dict[str, Any], force: bool) -> Dict[str, Any]:
    src = Path(item["src"])
    dest = ROOT / item["dest"]
    rec = inventory_item(item)
    if not src.exists():
        rec["action"] = "missing_src"
        rec["ok"] = bool(item.get("optional"))
        return rec

    skip_markers = item.get("skip_if_dest_has") or []
    if not force and skip_markers and all((dest / m).is_file() for m in skip_markers):
        rec["action"] = "preserve_dest_partial"

    stats = copy_tree(
        src,
        dest,
        force=force,
        exclude_dirs=set(item.get("exclude_dirs") or EXCLUDE_ALWAYS),
        glob=item.get("glob"),
        max_files=item.get("max_files"),
    )
    rec["action"] = rec.get("action") or "copied"
    rec["stats"] = stats
    rec["ok"] = True
    return rec


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Import external RealAI trees into RealAI-clean")
    ap.add_argument("--apply", action="store_true", help="Copy files (default is dry-run)")
    ap.add_argument("--force", action="store_true", help="Overwrite existing files")
    ap.add_argument("--id", action="append", help="Only these import ids")
    args = ap.parse_args(argv)

    selected = IMPORTS
    if args.id:
        want = set(args.id)
        selected = [i for i in IMPORTS if i["id"] in want]

    results = []
    for item in selected:
        if args.apply:
            results.append(apply_item(item, force=args.force))
        else:
            results.append(inventory_item(item))

    report = {
        "utc": utc(),
        "mode": "apply" if args.apply else "dry-run",
        "root": str(ROOT),
        "results": results,
        "runtime_extra_read": (
            "Set REALAI_EXTRA_READ_ROOTS=C:\\realai;D:\\realai_archives;... "
            "for opt-in read-only access without copy. Writes stay workspace-only."
        ),
        "sandbox_note": (
            "Default product mode: craft tools workspace-scoped. "
            "REALAI_ALLOW_EXTERNAL_READ alone is insufficient; use REALAI_EXTRA_READ_ROOTS."
        ),
    }

    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nWrote {LOG}", file=sys.stderr)

    hard_fail = [r for r in results if not r.get("src_exists") and not r.get("optional")]
    return 1 if hard_fail and args.apply else 0


if __name__ == "__main__":
    raise SystemExit(main())
