#!/usr/bin/env python3
"""
Catalog live trees that hold real (non-dump) RealAI code.

Writes scan_results/GOOD_CODE_ROOTS.json for craft /dispatch and promote phases.
Does not copy files — discovery only.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]

# Live product + recovered-gold places (relative to ROOT)
GOOD_CODE_ROOTS = [
    "abilities",
    "adapters",
    "agent_tools",
    "agents",
    "aura",
    "core",
    "modules",
    "plugins",
    "realai",
    "scripts",
    "tools",
    "training",
    "packages",
    "registry",
    "scanners",
    "server",
    # Quarantine = lost/unique gold for self-improve (bounded scanners handle size)
    "_quarantine",
    # High-signal import snapshots (not bulk recovered/)
    "imports/external/unique-modules",
    "imports/external/agent_tools_gold",
    "imports/external/C_realai_modules",
    "imports/external/C_realai_plugins",
    "imports/external/C_realai_server",
    "imports/external/orchestrators",
    "imports/external/self_improvement",
    "imports/external/organs",
    "imports/external/agents_advanced",
    "imports/external/agents_skills",
    "imports/external/desktop_unique",
    "imports/external/grok_export_realai",
    "imports/external/recovery_plugins",
]

SKIP_DIR_NAMES = {
    "node_modules", ".venv", "venv", "__pycache__", ".git",
    "dist", "build", ".tox", ".mypy_cache", ".ruff_cache",
    "site-packages", ".next", "checkpoints_lora",
}


def count_py(path: Path, limit_files: int = 5000) -> dict:
    n = 0
    sample: list[str] = []
    if not path.exists():
        return {"exists": False, "py_files": 0, "sample": []}
    if path.is_file():
        return {
            "exists": True,
            "py_files": 1 if path.suffix == ".py" else 0,
            "sample": [path.name] if path.suffix == ".py" else [],
        }
    for p in path.rglob("*.py"):
        if any(part in SKIP_DIR_NAMES for part in p.parts):
            continue
        n += 1
        if len(sample) < 12:
            try:
                sample.append(str(p.relative_to(ROOT)).replace("\\", "/"))
            except ValueError:
                sample.append(str(p))
        if n >= limit_files:
            break
    return {"exists": True, "py_files": n, "sample": sample}


def main() -> int:
    roots_out = []
    total = 0
    for rel in GOOD_CODE_ROOTS:
        p = ROOT / rel
        info = count_py(p)
        entry = {"rel": rel.replace("\\", "/"), **info}
        roots_out.append(entry)
        if info.get("exists") and info.get("py_files", 0) > 0:
            total += int(info["py_files"])
            print(f"[good] {rel}: {info['py_files']} py")
        elif info.get("exists"):
            print(f"[empty] {rel}")
        else:
            print(f"[missing] {rel}")

    present = [r for r in roots_out if r.get("exists") and r.get("py_files", 0) > 0]
    payload = {
        "version": 1,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "root": str(ROOT),
        "total_py_files_approx": total,
        "present_roots": [r["rel"] for r in present],
        "roots": roots_out,
        "notes": [
            "Prefer present_roots for scan/promote/dispatch.",
            "Avoid recovered/ bulk dumps; use imports/external/* gold packages.",
            "abilities/, core/, modules/, agent_tools/ are primary live product trees.",
        ],
    }

    out_dirs = [ROOT / "scan_results", ROOT / "recovered", ROOT / "scripts" / "recovered"]
    wrote = []
    for d in out_dirs:
        try:
            d.mkdir(parents=True, exist_ok=True)
            path = d / "GOOD_CODE_ROOTS.json"
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            wrote.append(str(path))
        except OSError as e:
            print(f"[warn] write failed {d}: {e}")

    print(f"[good] present_roots={len(present)} total_py≈{total}")
    print(f"[good] wrote {wrote}")
    return 0 if present else 1


if __name__ == "__main__":
    raise SystemExit(main())
