#!/usr/bin/env python3
"""
Ingest scripts/realai_roots_*.json (from scan_realai_roots.ps1) into self-heal.

Pipeline:
  load → dedupe → collapse nested paths → score promote/review candidates
  → write scan_results/realai_roots_ingest.json
  → assemble_gold_index.py consumes that into gold_index + promote_queue

This does NOT re-walk D:\\. It only processes the JSON inventory.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

ROOT = Path(os.environ.get("REALAI_ROOT", r"C:\RealAI-clean"))
SCRIPTS = ROOT / "scripts"
SCAN = ROOT / "scan_results"
OUT = SCAN / "realai_roots_ingest.json"

DEFAULT_INPUTS = [
    SCRIPTS / "realai_roots_D.json",
    SCRIPTS / "realai_roots_C.json",
    SCRIPTS / "realai_roots_B.json",
    SCRIPTS / "realai_roots_A.json",
]

NOISE_NAMES = {
    "node_modules",
    ".pnpm",
    "dist",
    "build",
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "cache",
    "logs",
    "blobs",
    "snapshots",
    "artifacts",
    ".trash-1000",
    ".github",
}

# Path fragments that mean "not RealAI gold" even if basename matches.
NOISE_PATH_PARTS = {
    "node_modules",
    ".pnpm",
    "program files",
    "program files (x86)",
    "windows",
    "appdata",
    "msi afterburner",
    "malwarebytes",
    "reference assemblies",
}

# Folder basenames that are high-signal for RealAI recovery.
HIGH_VALUE = {
    "realai",
    "realai-core",
    "realai-clean",
    "realai-overseer",
    "realai-embed",
    "realai-1.0",
    "realai-cli",
    "realai-sdk-js",
    "fusion-ui",
    "agent_tools",
    "agent-tools",
    "agent-tools-main",
    "abilities",
    "orchestration",
    "orchestrators",
    "tools_realai",
    "design-system",
    "aura",
    "hive",
    "self_heal",
    "self-heal",
}

# Common basenames — only keep when path also looks RealAI-related.
COMMON_BASENAMES = {
    "api",
    "cli",
    "sdk",
    "sdk-py",
    "sdk-ts",
    "models",
    "memory",
    "agents",
    "skills",
    "agent",
    "tools",
    "plugins",
    "providers",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm(path: str) -> str:
    return os.path.normcase(os.path.normpath(path.replace("/", "\\")))


def load_entries(paths: Sequence[Path]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[ingest] warn: failed to load {path}: {e}")
            continue
        if not isinstance(data, list):
            print(f"[ingest] warn: {path} is not a list, skipped")
            continue
        for item in data:
            if not isinstance(item, dict):
                continue
            full = item.get("FullPath") or item.get("path") or ""
            name = item.get("Name") or item.get("name") or Path(full).name
            if not full:
                continue
            rows.append(
                {
                    "Name": str(name),
                    "FullPath": str(full),
                    "source_file": str(path.name),
                }
            )
        print(f"[ingest] loaded {path.name}: {len(data)} rows")
    return rows


def era_of(full: str) -> str:
    low = full.lower().replace("/", "\\")
    if "\\realai-archive\\" in low or low.endswith("\\realai-archive") or "\\realai_archives\\" in low:
        return "archive"
    if "\\recovered\\" in low or "\\from_accident\\" in low:
        return "recovered"
    if "historical" in low or "backup" in low:
        return "backup"
    if "\\hf_cache\\" in low:
        return "models"
    return "external_d"


def subsystem_of(name: str, full: str) -> str:
    text = f"{name} {full}".lower()
    rules = [
        ("agents_hive", r"agent|hive|orchestrat|persona|agentx"),
        ("self_improve_training", r"self[_-]?heal|self[_-]?improv|finetun|training|lora"),
        ("memory_rag", r"memory|rag|embed|vector"),
        ("providers_models", r"model|provider|gguf|llama|qwen|hf_cache|inference"),
        ("ui_fusion_vscode", r"fusion|frontend|vscode|design-system|ui"),
        ("tools_mcp", r"tool|mcp|plugin|skill"),
        ("cli_sdk", r"\bcli\b|sdk"),
        ("server_api", r"\bapi\b|server"),
        ("web3_solana", r"solana|web3"),
        ("world_npc", r"aura|npc|world"),
    ]
    for sub, pat in rules:
        if re.search(pat, text, re.I):
            return sub
    return "other"


def is_noise_path(full: str) -> bool:
    low = full.lower().replace("/", "\\")
    parts = set(low.split("\\"))
    if parts & NOISE_NAMES:
        return True
    return any(frag in low for frag in NOISE_PATH_PARTS)


def looks_realai_context(full: str, name: str) -> bool:
    low = f"{full} {name}".lower()
    return any(
        tok in low
        for tok in (
            "realai",
            "fusion",
            "agent_tools",
            "agent-tools",
            "atomic",
            "fizz",
            "orchestr",
            "self_heal",
            "self-heal",
            "llama",
            "grok",
        )
    )


def score_candidate(
    *,
    name: str,
    full: str,
    depth: int,
    era: str,
    nested: bool,
) -> Tuple[str, int, str]:
    """Return (action, priority, reason)."""
    low_name = name.lower()
    if nested:
        return "skip_dup", 20, "nested_under_kept_root"
    if low_name in NOISE_NAMES or is_noise_path(full):
        return "skip_dup", 10, "noise_path"
    if depth >= 8:
        return "archive_only", 35, "too_deep"
    if low_name in HIGH_VALUE and depth <= 5:
        action = "promote" if era in ("recovered", "external_d", "backup") and depth <= 4 else "needs_review"
        return action, 90 + max(0, 5 - depth) * 2, "high_value_shallow_root"
    if low_name in HIGH_VALUE and looks_realai_context(full, name):
        return "needs_review", 70, "high_value_root"
    if low_name in COMMON_BASENAMES:
        if looks_realai_context(full, name) and depth <= 4:
            return "needs_review", 60, "common_basename_realai_context"
        return "skip_dup", 15, "common_basename_unrelated"
    if "realai" in low_name:
        return "needs_review" if depth <= 6 else "archive_only", 75 if depth <= 6 else 40, "realai_named"
    if looks_realai_context(full, name) and depth <= 4:
        return "needs_review", 50, "realai_context_shallow"
    return "archive_only", 25, "inventory_only"


def collapse_nested(sorted_paths: List[str]) -> Set[str]:
    """Mark paths that sit under an earlier kept path as nested."""
    nested: Set[str] = set()
    kept: List[str] = []
    for p in sorted_paths:
        is_nested = False
        for parent in kept:
            if p.startswith(parent + "\\"):
                nested.add(p)
                is_nested = True
                break
        if not is_nested:
            kept.append(p)
    return nested


def ingest(inputs: Sequence[Path], max_queue: int = 250) -> Dict[str, Any]:
    raw = load_entries(inputs)
    # Dedupe by normalized full path (keep first source).
    by_path: Dict[str, Dict[str, str]] = {}
    for row in raw:
        key = norm(row["FullPath"])
        if key not in by_path:
            by_path[key] = row

    deduped = list(by_path.values())
    # Drop obvious junk before collapse so node_modules/Program Files never become parents.
    usable = [
        r
        for r in deduped
        if r["Name"].lower() not in NOISE_NAMES and not is_noise_path(r["FullPath"])
    ]
    usable.sort(key=lambda r: (norm(r["FullPath"]).count("\\"), norm(r["FullPath"]).lower()))
    norms = [norm(r["FullPath"]) for r in usable]
    nested = collapse_nested(norms)

    candidates: List[Dict[str, Any]] = []
    action_counts: Counter = Counter()
    era_counts: Counter = Counter()
    source_counts: Counter = Counter()

    # Still record skipped noise for stats, but don't queue them.
    noise_skipped = len(deduped) - len(usable)
    action_counts["skip_dup"] += noise_skipped

    for row in usable:
        full = row["FullPath"]
        nfull = norm(full)
        name = row["Name"]
        depth = len(Path(nfull).parts)
        era = era_of(full)
        action, priority, reason = score_candidate(
            name=name,
            full=full,
            depth=depth,
            era=era,
            nested=nfull in nested,
        )
        sub = subsystem_of(name, full)
        item = {
            "id": f"droot:{nfull}",
            "path": full.replace("\\", "/"),
            "name": name,
            "era": era,
            "subsystem": sub,
            "action": action,
            "target": f"recovered/from_d_roots/{name}",
            "reasons": [f"realai_roots:{reason}"],
            "sources": ["realai_roots_json", row.get("source_file") or "unknown"],
            "priority": priority,
            "extra": {
                "depth": depth,
                "source_file": row.get("source_file"),
                "nested": nfull in nested,
            },
        }
        candidates.append(item)
        action_counts[action] += 1
        era_counts[era] += 1
        source_counts[row.get("source_file") or "unknown"] += 1

    # Rank actionable items for assemble/promote queue (cap).
    actionable = [
        c
        for c in candidates
        if c["action"] in ("promote", "needs_review", "rewrite")
    ]
    actionable.sort(key=lambda x: (-x["priority"], x["extra"]["depth"], x["path"].lower()))
    queue = actionable[: max(1, max_queue)]

    # Compact top roots for humans / architect.
    top_roots = [
        {
            "name": c["name"],
            "path": c["path"],
            "action": c["action"],
            "priority": c["priority"],
            "subsystem": c["subsystem"],
            "era": c["era"],
            "depth": c["extra"]["depth"],
        }
        for c in queue[:50]
    ]

    payload = {
        "meta": {
            "generated_at": utc_now(),
            "root": str(ROOT),
            "inputs": [str(p) for p in inputs if p.is_file()],
            "raw_rows": len(raw),
            "deduped_rows": len(deduped),
            "usable_rows": len(usable),
            "noise_skipped": noise_skipped,
            "nested_collapsed": len(nested),
            "max_queue": max_queue,
            "by_action": dict(action_counts),
            "by_era": dict(era_counts),
            "by_source_file": dict(source_counts),
            "actionable_total": len(actionable),
            "actionable_queued": len(queue),
            "note": "Folder-root inventory from D: scan JSON. Caps actionable queue to avoid flooding promote.",
        },
        "top_roots": top_roots,
        "queue": queue,
        # Keep a lighter sample of skips for debugging (not full 33k).
        "skip_sample": [c for c in candidates if c["action"] == "skip_dup"][:100],
        "archive_sample": [c for c in candidates if c["action"] == "archive_only"][:100],
    }
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Ingest realai_roots_*.json into self-heal scan_results")
    ap.add_argument(
        "--input",
        action="append",
        default=[],
        help="JSON path (repeatable). Default: scripts/realai_roots_{D,C,B,A}.json that exist",
    )
    ap.add_argument("--max-queue", type=int, default=250, help="Max promote/needs_review candidates")
    args = ap.parse_args(list(argv) if argv is not None else None)

    inputs = [Path(p) for p in args.input] if args.input else list(DEFAULT_INPUTS)
    existing = [p for p in inputs if p.is_file()]
    if not existing:
        print("[ingest] no input JSON found")
        print("  looked for:", ", ".join(str(p) for p in inputs))
        return 1

    print(f"[ingest] REALAI_ROOT={ROOT}")
    payload = ingest(existing, max_queue=args.max_queue)
    SCAN.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    meta = payload["meta"]
    print(f"[ingest] -> {OUT}")
    print(
        f"[ingest] raw={meta['raw_rows']} deduped={meta['deduped_rows']} "
        f"nested={meta['nested_collapsed']} queued={meta['actionable_queued']}/{meta['actionable_total']}"
    )
    print("[ingest] by_action:", meta["by_action"])
    print("[ingest] top queued:")
    for it in payload["queue"][:15]:
        print(
            f"  [{it['priority']}] {it['action']:12} {it['subsystem']:22} "
            f"d={it['extra']['depth']} {it['path'][:80]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
