#!/usr/bin/env python3
"""
Phase 2: Promote gold from promote_queue.json into authority / staging.

Default: --dry-run (no writes)
Apply:    --apply

Safety:
  - Never overwrite authority files with different content without --force
  - Skip scanners/*, cavity scripts, noise
  - Deduplicate by content hash (one copy per unique blob)
  - Memory snapshots → recovered/ only (never live DB paths)
  - Training Downloads → training/data/
  - agentx / registryClient → confirm authority paths
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(r"C:\realai")
QUEUE = ROOT / "scan_results" / "promote_queue.json"
LOG = ROOT / "recovered" / "PROMOTE_LOG.json"
REPORT = ROOT / "scan_results" / "phase2_promote_report.md"

# Paths we never promote as product code
SKIP_PREFIXES = (
    "scanners/",
    "scan_results/",
    "phase4_tools/",
    "node_modules/",
    "venv/",
    ".venv/",
    "manifests/",
)
SKIP_NAMES = {
    "dds3_missing_files.py",
    "dds1_dependency_doc_scan.py",
    "dds3_deep_gold_map.py",
    "fs1_full_spectrum_scan.py",
    "lora_scan.py",
    "mcp_scan.py",
    "npc_scan.py",
    "solana_scan.py",
    "rag_scan.py",
    "realai_alt_cavity_search.py",
    "realai_alt_v2_cavity_search.py",
    "realai_alt_v3_cavity_search.py",
    "realai_full_cavity_search.py",
    "realai_full_spectrum_scan.py",
    "realai_full_module_scan.py",
    "realai_tri_cavity_search.py",
    "dry_run_scaffold.py",
    "smart_merge_realai.py",
    "orchestrator.py",
}

# basename → preferred authority/staging target
CANONICAL_TARGETS = {
    "registryClient.ts": "packages/sdk-ts/src/registryClient.ts",
    "envChatClient.ts": "packages/sdk-ts/src/envChatClient.ts",
    "realaiClient.ts": "packages/sdk-ts/src/envChatClient.ts",  # archive name
    "agents.json": "agents/agentx/agents.json",
    "access_profiles.json": "agents/agentx/access_profiles.json",
    "agency_import.json": "agents/agentx/agency_import.json",
    "realai_finetune_dataset.jsonl": "training/data/realai_finetune_dataset.jsonl",
    "agent_manifests_for_finetuning.json": "training/data/agent_manifests_for_finetuning.json",
}

MEMORY_NAMES = {
    "realai_memory.json",
    "realai_memory.db",
    "realai_memory.sqlite3",
    "realai_knowledge_store.json",
    "realai_memory__dup1.sqlite3",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def resolve_src(path_str: str) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    # Windows absolute sometimes as C:/...
    if len(path_str) > 2 and path_str[1] == ":":
        return Path(path_str)
    return ROOT / path_str.replace("/", "\\")


def should_skip_item(item: Dict[str, Any]) -> Tuple[bool, str]:
    path = item.get("path", "").replace("\\", "/")
    name = Path(path).name
    low = path.lower()

    if item.get("action") in ("skip_dup", "archive_only"):
        return True, f"action={item.get('action')}"

    if name in SKIP_NAMES:
        return True, "discovery_tool_not_product"

    for pref in SKIP_PREFIXES:
        if low.startswith(pref) or f"/{pref}" in f"/{low}":
            return True, f"skip_prefix:{pref}"

    if path.startswith("missing:") or path.startswith("capability:"):
        return True, "token_not_file"

    if "scanners/" in low:
        return True, "scanner_script"

    # ability_file under clean already
    if item.get("era") == "clean" and item.get("action") == "promote":
        return True, "already_clean_era"

    return False, ""


def plan_target(item: Dict[str, Any]) -> Tuple[Optional[str], str]:
    """Return (relative_target, kind) or (None, reason_skip)."""
    path = item.get("path", "").replace("\\", "/")
    name = Path(path).name
    reason = " ".join(item.get("reasons") or [])
    action = item.get("action")

    # Training downloads
    if "Downloads" in path or "downloads" in path.lower():
        if name in CANONICAL_TARGETS:
            return CANONICAL_TARGETS[name], "training_import"
        return f"training/data/{name}", "training_import"

    # Memory — staging only
    if name in MEMORY_NAMES or "memory" in reason.lower() and name.endswith((".json", ".db", ".sqlite3")):
        # keep under recovered with unique hash suffix later
        return f"recovered/from_archive/memory_snapshots/{name}", "memory_staging"

    # Canonical basename map
    if name in CANONICAL_TARGETS:
        return CANONICAL_TARGETS[name], "canonical"

    # needs_review non-memory → recovered staging
    if action == "needs_review":
        return f"recovered/from_gold/{item.get('subsystem','other')}/{name}", "review_staging"

    # promote source code with sensible homes
    if name.endswith((".ts", ".tsx", ".js")):
        if "ui" in path or "Client" in name or "frontend" in path:
            return f"packages/sdk-ts/src/{name}", "ui_sdk"
        return f"recovered/from_gold/ts/{name}", "ts_staging"

    if name.endswith(".py"):
        if name.startswith("realai_") or "self" in name:
            return f"recovered/from_gold/py/{name}", "py_staging"
        return f"recovered/from_gold/py/{name}", "py_staging"

    if name.endswith((".json", ".yaml", ".yml", ".md")):
        return f"recovered/from_gold/meta/{name}", "meta_staging"

    return f"recovered/from_gold/misc/{name}", "misc_staging"


def dedupe_key(src: Path) -> str:
    h = sha256(src)
    return h or f"path:{src}"


def process_queue(apply: bool, include_review: bool) -> Dict[str, Any]:
    data = json.loads(QUEUE.read_text(encoding="utf-8"))
    queue: List[Dict[str, Any]] = data.get("queue") or []

    seen_hashes: Set[str] = set()
    actions: List[Dict[str, Any]] = []
    stats = {
        "considered": 0,
        "skipped": 0,
        "would_copy": 0,
        "copied": 0,
        "already_identical": 0,
        "missing_source": 0,
        "errors": 0,
    }

    for item in queue:
        stats["considered"] += 1
        skip, why = should_skip_item(item)
        if skip:
            stats["skipped"] += 1
            actions.append({"status": "skipped", "why": why, "path": item.get("path")})
            continue

        src = resolve_src(item["path"])
        if not src.is_file():
            alt = ROOT / item["path"].replace("/", "\\")
            if alt.is_file():
                src = alt
            else:
                stats["missing_source"] += 1
                actions.append({"status": "missing_source", "path": item.get("path")})
                continue

        target_rel, kind = plan_target(item)
        if not target_rel:
            stats["skipped"] += 1
            actions.append({"status": "skipped", "why": kind, "path": str(src)})
            continue

        action = item.get("action")
        if action not in ("promote", "needs_review", "rewrite"):
            stats["skipped"] += 1
            continue

        # needs_review: only memory staging unless --include-review
        if action == "needs_review" and kind not in ("memory_staging", "training_import"):
            if not include_review:
                stats["skipped"] += 1
                actions.append({
                    "status": "skipped",
                    "why": "needs_review_hold",
                    "path": item.get("path"),
                    "would_target": target_rel,
                })
                continue

        h = dedupe_key(src)
        if h in seen_hashes:
            stats["skipped"] += 1
            actions.append({
                "status": "skipped",
                "why": "duplicate_content_hash",
                "path": str(src),
                "sha256": h[:16],
            })
            continue
        seen_hashes.add(h)

        # unique memory filename with hash prefix if collision risk
        if kind == "memory_staging":
            short = h[:12]
            stem = Path(target_rel).stem
            suf = Path(target_rel).suffix
            target_rel = f"recovered/from_archive/memory_snapshots/{stem}__{short}{suf}"

        dst = ROOT / target_rel.replace("/", "\\")

        entry = {
            "status": "planned",
            "kind": kind,
            "src": str(src),
            "dst": str(dst.relative_to(ROOT)).replace("\\", "/"),
            "sha256": h,
            "size": src.stat().st_size,
            "queue_id": item.get("id"),
            "subsystem": item.get("subsystem"),
            "action": item.get("action"),
        }

        if dst.exists():
            dh = sha256(dst)
            if dh == h:
                entry["status"] = "already_identical"
                stats["already_identical"] += 1
                actions.append(entry)
                continue
            # different content — do not overwrite authority without force
            entry["status"] = "conflict_exists"
            entry["existing_sha"] = dh
            stats["skipped"] += 1
            actions.append(entry)
            continue

        if not apply:
            entry["status"] = "would_copy"
            stats["would_copy"] += 1
            actions.append(entry)
            continue

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            entry["status"] = "copied"
            stats["copied"] += 1
            actions.append(entry)
            print(f"  + {entry['dst']}")
        except Exception as e:
            entry["status"] = "error"
            entry["error"] = str(e)
            stats["errors"] += 1
            actions.append(entry)

    # Always ensure training/data exists and mirror agentx if needed (apply only)
    return {
        "meta": {
            "generated_at": utc_now(),
            "apply": apply,
            "include_review": include_review,
            "queue_path": str(QUEUE),
            "stats": stats,
        },
        "actions": actions,
    }


def write_report(result: Dict[str, Any]) -> None:
    stats = result["meta"]["stats"]
    lines = [
        "# Phase 2 Promote Report",
        "",
        f"Generated: `{result['meta']['generated_at']}`",
        f"Mode: **{'APPLY' if result['meta']['apply'] else 'DRY-RUN'}**",
        "",
        "## Stats",
        "",
    ]
    for k, v in stats.items():
        lines.append(f"- **{k}:** {v}")
    lines.append("")
    lines.append("## Copied / would_copy")
    lines.append("")
    for a in result["actions"]:
        if a.get("status") in ("copied", "would_copy", "already_identical"):
            lines.append(
                f"- `{a['status']}` · `{a.get('src','')}` → `{a.get('dst','')}`"
            )
    lines.append("")
    lines.append("## Conflicts (not overwritten)")
    lines.append("")
    conflicts = [a for a in result["actions"] if a.get("status") == "conflict_exists"]
    if not conflicts:
        lines.append("- (none)")
    else:
        for a in conflicts:
            lines.append(f"- `{a.get('src')}` vs existing `{a.get('dst')}`")
    lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 2 promote gold from promote_queue")
    ap.add_argument("--apply", action="store_true", help="Actually copy files")
    ap.add_argument(
        "--include-review",
        action="store_true",
        help="Also stage needs_review non-memory items into recovered/from_gold",
    )
    ap.add_argument(
        "--memory",
        action="store_true",
        help="Include memory snapshot staging to recovered/",
    )
    args = ap.parse_args()

    if not QUEUE.exists():
        print(f"Missing queue: {QUEUE}")
        return 2

    # If --memory, treat memory needs_review as includable via plan_target
    include_review = args.include_review or args.memory

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[promote] {mode} root={ROOT}")
    result = process_queue(apply=args.apply, include_review=include_review)

    # Special path: always handle training + ensure agentx/registry present on apply
    # Re-run focused high-value list
    high_value = [
        (
            Path(r"C:\Users\tsmit\Downloads\realai_finetune_dataset.jsonl"),
            ROOT / "training" / "data" / "realai_finetune_dataset.jsonl",
        ),
        (
            Path(r"C:\Users\tsmit\Downloads\agent_manifests_for_finetuning.json"),
            ROOT / "training" / "data" / "agent_manifests_for_finetuning.json",
        ),
    ]
    for src, dst in high_value:
        if not src.is_file():
            result["actions"].append({"status": "missing_source", "path": str(src)})
            result["meta"]["stats"]["missing_source"] += 1
            continue
        h = sha256(src)
        if dst.exists() and sha256(dst) == h:
            result["actions"].append({
                "status": "already_identical",
                "src": str(src),
                "dst": str(dst.relative_to(ROOT)).replace("\\", "/"),
                "kind": "training_import",
            })
            result["meta"]["stats"]["already_identical"] += 1
            continue
        if not args.apply:
            result["actions"].append({
                "status": "would_copy",
                "src": str(src),
                "dst": str(dst.relative_to(ROOT)).replace("\\", "/"),
                "kind": "training_import",
                "size": src.stat().st_size,
            })
            result["meta"]["stats"]["would_copy"] += 1
            print(f"  would: {dst.relative_to(ROOT)}")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            result["actions"].append({
                "status": "copied",
                "src": str(src),
                "dst": str(dst.relative_to(ROOT)).replace("\\", "/"),
                "kind": "training_import",
                "size": src.stat().st_size,
            })
            result["meta"]["stats"]["copied"] += 1
            print(f"  + {dst.relative_to(ROOT)}")

    # Mirror registryClient into realai packages if missing
    sdk_src = ROOT / "packages" / "sdk-ts" / "src" / "registryClient.ts"
    sdk_dst = ROOT / "realai" / "packages" / "sdk-ts" / "src" / "registryClient.ts"
    if sdk_src.is_file():
        if not args.apply:
            if not sdk_dst.exists() or sha256(sdk_src) != sha256(sdk_dst):
                result["actions"].append({
                    "status": "would_copy",
                    "src": str(sdk_src),
                    "dst": str(sdk_dst.relative_to(ROOT)).replace("\\", "/"),
                    "kind": "sdk_mirror",
                })
                result["meta"]["stats"]["would_copy"] += 1
        else:
            if not sdk_dst.exists() or sha256(sdk_src) != sha256(sdk_dst):
                sdk_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(sdk_src, sdk_dst)
                result["actions"].append({
                    "status": "copied",
                    "src": str(sdk_src),
                    "dst": str(sdk_dst.relative_to(ROOT)).replace("\\", "/"),
                    "kind": "sdk_mirror",
                })
                result["meta"]["stats"]["copied"] += 1
                print(f"  + {sdk_dst.relative_to(ROOT)}")

    # README for training data
    train_readme = ROOT / "training" / "data" / "README.md"
    if args.apply:
        train_readme.parent.mkdir(parents=True, exist_ok=True)
        if not train_readme.exists():
            train_readme.write_text(
                "# Training data (promoted Phase 2)\n\n"
                "- `realai_finetune_dataset.jsonl` — instruction/response samples\n"
                "- `agent_manifests_for_finetuning.json` — agent roles for finetune\n\n"
                "Imported from Downloads. Use with `realai/training` / self_improvement pipeline.\n",
                encoding="utf-8",
            )

    write_report(result)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"[promote] stats: {result['meta']['stats']}")
    print(f"[promote] log -> {LOG}")
    print(f"[promote] report -> {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
