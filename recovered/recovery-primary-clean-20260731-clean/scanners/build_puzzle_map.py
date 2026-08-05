#!/usr/bin/env python3
"""
Build a single puzzle map from existing scanners + artifacts.

Does NOT re-walk the super-repo. Only indexes scripts and known output files
so you can see what exists, what is huge, and what to open first.

Outputs:
  scan_results/puzzle_map.json
  scan_results/puzzle_map.md
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

ROOT = os.environ.get("REALAI_ROOT", r"C:\realai")
OUT_DIR = os.path.join(ROOT, "scan_results")
OUT_JSON = os.path.join(OUT_DIR, "puzzle_map.json")
OUT_MD = os.path.join(OUT_DIR, "puzzle_map.md")

# Catalog of known discovery tools (the puzzle pieces)
# trust: high | medium | low | archaeology | noise_if_huge
CATALOG: List[Dict[str, Any]] = [
    # --- Gen 0 root ---
    {
        "id": "gen0-tri-cavity",
        "generation": 0,
        "script": "realai_tri_cavity_search.py",
        "outputs": ["manifests/tri_cavity_manifest.json"],
        "purpose": "Early 3-group keyword cavity search",
        "trust": "archaeology",
        "open_first": False,
    },
    {
        "id": "gen0-alt-v2",
        "generation": 0,
        "script": "realai_alt_v2_cavity_search.py",
        "outputs": ["manifests/alt_v2_cavity_manifest.json"],
        "purpose": "Alt keyword cavity v2",
        "trust": "archaeology",
        "open_first": False,
    },
    {
        "id": "gen0-alt-v3",
        "generation": 0,
        "script": "realai_alt_v3_cavity_search.py",
        "outputs": ["manifests/alt_v3_cavity_manifest.json"],
        "purpose": "Alt keyword cavity v3",
        "trust": "archaeology",
        "open_first": False,
    },
    {
        "id": "gen0-alt-cavity",
        "generation": 0,
        "script": "realai_alt_cavity_search.py",
        "outputs": [
            "manifests/realai_alt_cavity_manifest.json",
            "realai_alt_cavity_summary.txt",
        ],
        "purpose": "Massive keyword dump (multi-GB risk)",
        "trust": "noise_if_huge",
        "open_first": False,
        "do_not_rerun": True,
    },
    {
        "id": "gen0-full-cavity",
        "generation": 0,
        "script": "realai_full_cavity_search.py",
        "outputs": [
            "manifests/realai_full_cavity_manifest.json",
            "realai_full_cavity_summary.txt",
        ],
        "purpose": "Full keyword cavity + group summaries",
        "trust": "archaeology",
        "open_first": False,
        "do_not_rerun": True,
    },
    {
        "id": "gen0-full-spectrum",
        "generation": 0,
        "script": "realai_full_spectrum_scan.py",
        "outputs": ["manifests/full_spectrum_cavity_manifest.json"],
        "purpose": "Spectrum keyword scan (root copy)",
        "trust": "archaeology",
        "open_first": False,
    },
    {
        "id": "gen0-full-module",
        "generation": 0,
        "script": "realai_full_module_scan.py",
        "outputs": ["manifests/full_module_manifest.json"],
        "purpose": "Module listing (root copy)",
        "trust": "archaeology",
        "open_first": False,
    },
    {
        "id": "gen0-orchestrator",
        "generation": 0,
        "script": "orchestrator.py",
        "outputs": [],
        "purpose": "Phase scan/patch-target orchestrator (design)",
        "trust": "medium",
        "open_first": False,
    },
    {
        "id": "gen0-dry-run",
        "generation": 0,
        "script": "dry_run_scaffold.py",
        "outputs": [
            "phase4_tools/plan_phase4_preview/phase4_preview_summary.txt",
            "phase4_tools/plan_phase4_preview/phase4_preview.json",
        ],
        "purpose": "Phase-4 merge dry-run preview",
        "trust": "medium",
        "open_first": True,
        "note": "Use SUMMARY counts only; do not execute bulk merge yet",
    },
    {
        "id": "gen0-smart-merge",
        "generation": 0,
        "script": "smart_merge_realai.py",
        "outputs": [],
        "purpose": "Early merge helper — do not bulk-run",
        "trust": "low",
        "open_first": False,
        "do_not_rerun": True,
    },
    # --- Gen 2 scanners/ ---
    {
        "id": "fs1",
        "generation": 2,
        "script": "scanners/fs1_full_spectrum_scan.py",
        "outputs": ["scan_results/fs1_full_spectrum_manifest.json"],
        "purpose": "Full spectrum feature keywords",
        "trust": "medium",
        "open_first": False,
    },
    {
        "id": "fs2",
        "generation": 2,
        "script": "scanners/fs2_module_scan.py",
        "outputs": ["scan_results/fs2_module_manifest.json"],
        "purpose": "Module inventory",
        "trust": "medium",
        "open_first": False,
    },
    {
        "id": "alt-v4",
        "generation": 2,
        "script": "scanners/alt_v4_autonomy_scan.py",
        "outputs": ["scan_results/alt_v4_autonomy_manifest.json"],
        "purpose": "Autonomy keywords",
        "trust": "medium",
        "open_first": False,
    },
    {
        "id": "tri-v2",
        "generation": 2,
        "script": "scanners/tri_v2_worldmodel_scan.py",
        "outputs": ["scan_results/tri_v2_worldmodel_manifest.json"],
        "purpose": "World-model keywords",
        "trust": "medium",
        "open_first": False,
    },
    {
        "id": "lora",
        "generation": 2,
        "script": "scanners/lora_scan.py",
        "outputs": ["scan_results/lora_manifest.json"],
        "purpose": "LoRA / training surface",
        "trust": "medium",
        "open_first": False,
    },
    {
        "id": "rag",
        "generation": 2,
        "script": "scanners/rag_scan.py",
        "outputs": ["scan_results/rag_manifest.json"],
        "purpose": "RAG / retrieval surface",
        "trust": "medium",
        "open_first": False,
    },
    {
        "id": "mcp",
        "generation": 2,
        "script": "scanners/mcp_scan.py",
        "outputs": ["scan_results/mcp_manifest.json"],
        "purpose": "MCP / tools surface",
        "trust": "medium",
        "open_first": False,
    },
    {
        "id": "npc",
        "generation": 2,
        "script": "scanners/npc_scan.py",
        "outputs": ["scan_results/npc_manifest.json"],
        "purpose": "NPC / game surface",
        "trust": "medium",
        "open_first": False,
    },
    {
        "id": "solana",
        "generation": 2,
        "script": "scanners/solana_scan.py",
        "outputs": ["scan_results/solana_manifest.json"],
        "purpose": "Solana / web3 surface",
        "trust": "medium",
        "open_first": False,
    },
    {
        "id": "backend",
        "generation": 2,
        "script": "scanners/backend_scan.py",
        "outputs": ["scan_results/backend_manifest.json"],
        "purpose": "Backend surface",
        "trust": "medium",
        "open_first": False,
    },
    # --- Gen 3 DDS ---
    {
        "id": "dds1",
        "generation": 3,
        "script": "scanners/dds1_dependency_doc_scan.py",
        "outputs": ["scan_results/dds1_dependency_doc_manifest.json"],
        "purpose": "Dependency + documentation keywords",
        "trust": "medium",
        "open_first": False,
    },
    {
        "id": "dds2",
        "generation": 3,
        "script": "scanners/dds2_dependency_crosscheck.py",
        "outputs": ["scan_results/dds2_dependency_crosscheck.json"],
        "purpose": "Dependency cross-check",
        "trust": "medium",
        "open_first": False,
    },
    {
        "id": "dds3",
        "generation": 3,
        "script": "scanners/dds3_missing_files.py",
        "outputs": [
            "scan_results/dds3_missing_files.json",
            "scan_results/dds3_missing_files_summary.json",
            "scan_results/dds3_archive_triage.json",
            "scan_results/dds3_ability_inventory.json",
        ],
        "purpose": "Scoped missing map + archive triage + ability inventory",
        "trust": "high",
        "open_first": True,
        "note": "Primary scanner after polish. Run operational + archive + abilities.",
    },
    {
        "id": "dds4",
        "generation": 3,
        "script": "scanners/dds4_orphan_modules.py",
        "outputs": ["scan_results/dds4_orphan_modules.json"],
        "purpose": "Orphan modules",
        "trust": "medium",
        "open_first": False,
    },
    {
        "id": "dds5",
        "generation": 3,
        "script": "scanners/dds5_unused_features.py",
        "outputs": ["scan_results/dds5_unused_features.json"],
        "purpose": "Unused feature symbols (often huge/noisy)",
        "trust": "low",
        "open_first": False,
    },
    {
        "id": "dds6",
        "generation": 3,
        "script": "scanners/dds6_config_mismatches.py",
        "outputs": ["scan_results/dds6_config_mismatches.json"],
        "purpose": "Config mismatches",
        "trust": "medium",
        "open_first": False,
    },
    {
        "id": "dds7",
        "generation": 3,
        "script": "scanners/dds7_doc_code_consistency.py",
        "outputs": ["scan_results/dds7_doc_code_consistency.json"],
        "purpose": "Doc vs code consistency",
        "trust": "medium",
        "open_first": False,
    },
    {
        "id": "dds8",
        "generation": 3,
        "script": "scanners/dds8_runtime_path_integrity.py",
        "outputs": ["scan_results/dds8_runtime_path_integrity.json"],
        "purpose": "Runtime path integrity (re-scope before trusting)",
        "trust": "low",
        "open_first": False,
    },
    {
        "id": "dds9-deep",
        "generation": 3,
        "script": "scanners/dds9_subsystem_completeness_deep.py",
        "outputs": [
            "scan_results/dds9_subsystem_completeness_deep.json",
            "scan_results/dds9_subsystem_completeness.json",
        ],
        "purpose": "Subsystem completeness",
        "trust": "medium",
        "open_first": False,
    },
    {
        "id": "dds10",
        "generation": 3,
        "script": "scanners/dds10_merge_plan_validator.py",
        "outputs": ["scan_results/dds10_merge_plan_validator.json"],
        "purpose": "Validate Phase-4 merge plan structure",
        "trust": "high",
        "open_first": True,
        "note": "Validates plan files only; does not walk product code",
    },
    {
        "id": "puzzle-map",
        "generation": 4,
        "script": "scanners/build_puzzle_map.py",
        "outputs": [
            "scan_results/puzzle_map.json",
            "scan_results/puzzle_map.md",
            "scanners/PUZZLE_MAP.md",
        ],
        "purpose": "This index — consolidates the puzzle without re-crawling",
        "trust": "high",
        "open_first": True,
    },
]

# Decision order for humans
READ_ORDER = [
    ("scanners/PUZZLE_MAP.md", "Narrative map of every generation"),
    ("scan_results/puzzle_map.md", "Auto checklist with file sizes"),
    ("scan_results/dds3_missing_files_summary.json", "Scoped missing overview"),
    ("scan_results/dds3_archive_triage.json", "Accidental moves in archive/"),
    ("scan_results/dds3_ability_inventory.json", "Multi-era abilities to preserve"),
    ("phase4_tools/plan_phase4_preview/phase4_preview_summary.txt", "Merge counts only"),
    ("realai/api_server.py", "Boot spine (clean runtime)"),
]


def file_info(rel: str) -> Dict[str, Any]:
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(path):
        return {
            "path": rel,
            "exists": False,
            "size": 0,
            "size_human": "—",
            "mtime": None,
        }
    st = os.stat(path)
    size = st.st_size
    return {
        "path": rel,
        "exists": True,
        "size": size,
        "size_human": human_size(size),
        "mtime": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
        "open_advice": open_advice(size, rel),
    }


def human_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    for unit, div in (("KB", 1024), ("MB", 1024**2), ("GB", 1024**3)):
        if n < div * 1024 or unit == "GB":
            return f"{n / div:.1f} {unit}"
    return f"{n} B"


def open_advice(size: int, rel: str) -> str:
    lower = rel.lower()
    if size >= 100 * 1024 * 1024:
        return "TOO_LARGE_for_editor — use summary only or jq filters"
    if size >= 5 * 1024 * 1024:
        return "Large — open summary/top keys only"
    if "summary" in lower or "puzzle_map" in lower or "triage" in lower:
        return "Safe to open"
    if "ability" in lower or "dds3_missing" in lower:
        return "Safe to open (primary)"
    return "OK if needed"


def discover_orphan_outputs() -> List[Dict[str, Any]]:
    """List scan_results + manifests files not in catalog."""
    known = set()
    for entry in CATALOG:
        for o in entry.get("outputs", []):
            known.add(o.replace("\\", "/"))

    orphans = []
    for folder in ("scan_results", "manifests"):
        base = os.path.join(ROOT, folder)
        if not os.path.isdir(base):
            continue
        for name in os.listdir(base):
            full = os.path.join(base, name)
            if not os.path.isfile(full):
                continue
            rel = f"{folder}/{name}".replace("\\", "/")
            if rel not in known:
                orphans.append(file_info(rel))
    return orphans


def build() -> Dict[str, Any]:
    pieces = []
    for entry in CATALOG:
        script_rel = entry["script"]
        script_path = os.path.join(ROOT, script_rel.replace("/", os.sep))
        outputs = [file_info(o) for o in entry.get("outputs", [])]
        existing_out = [o for o in outputs if o["exists"]]
        total_out = sum(o["size"] for o in existing_out)
        pieces.append({
            **entry,
            "script_exists": os.path.isfile(script_path),
            "outputs_detail": outputs,
            "outputs_present": len(existing_out),
            "outputs_total_size": total_out,
            "outputs_total_size_human": human_size(total_out) if existing_out else "—",
            "status": status_for(entry, script_path, existing_out),
        })

    open_first = [p for p in pieces if p.get("open_first") and p["script_exists"]]
    missing_scripts = [p for p in pieces if not p["script_exists"]]
    huge = [
        o
        for p in pieces
        for o in p["outputs_detail"]
        if o["exists"] and o["size"] >= 50 * 1024 * 1024
    ]

    # Pull quick facts from high-trust JSON if present
    facts: Dict[str, Any] = {}
    facts.update(safe_json_facts("scan_results/dds3_missing_files_summary.json", [
        ("unique_missing", lambda d: d.get("unique_missing")),
        ("files_scanned", lambda d: d.get("meta", {}).get("files_scanned")),
        ("by_era", lambda d: d.get("by_era")),
    ]))
    facts.update(safe_json_facts("scan_results/dds3_archive_triage.json", [
        ("archive_recover_candidates", lambda d: d.get("counts", {}).get("recover_candidates")),
        ("archive_only_in_archive", lambda d: d.get("counts", {}).get("only_in_archive")),
        ("archive_memory_snapshots", lambda d: d.get("counts", {}).get("memory_snapshots")),
    ]))
    facts.update(safe_json_facts("scan_results/dds3_ability_inventory.json", [
        ("ability_tokens", lambda d: d.get("meta", {}).get("unique_tokens")),
        ("ability_only_outside_clean", lambda d: d.get("counts", {}).get("only_outside_clean")),
        ("ability_multi_era", lambda d: d.get("counts", {}).get("multi_era")),
    ]))

    return {
        "meta": {
            "root": ROOT,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "purpose": (
                "Index of all discovery scanners and artifacts. "
                "Does not re-crawl the repo. Use to sort the puzzle."
            ),
            "decision_order": [
                "1. Boot clean realai/ package",
                "2. dds3_archive_triage recover candidates",
                "3. dds3_ability_inventory only_outside_clean",
                "4. dds3_missing_files_summary",
                "5. Phase-4 summary counts (not bulk merge)",
                "6. Ignore multi-GB cavity JSON as primary truth",
            ],
        },
        "facts_from_high_trust": facts,
        "read_order": [{"path": p, "why": w} for p, w in READ_ORDER],
        "pieces": pieces,
        "open_first_pieces": [p["id"] for p in open_first],
        "missing_scripts": [p["id"] for p in missing_scripts],
        "huge_artifacts": huge,
        "orphan_outputs": discover_orphan_outputs(),
        "counts": {
            "catalog_pieces": len(pieces),
            "scripts_present": sum(1 for p in pieces if p["script_exists"]),
            "open_first": len(open_first),
            "huge_artifacts": len(huge),
        },
    }


def status_for(entry: Dict[str, Any], script_path: str, existing_out: List[dict]) -> str:
    if not os.path.isfile(script_path):
        return "script_missing"
    if entry.get("do_not_rerun") and existing_out:
        return "done_do_not_rerun"
    if entry.get("open_first") and existing_out:
        return "ready_open_first"
    if existing_out:
        return "has_output"
    return "script_only_no_output_yet"


def safe_json_facts(rel: str, extractors) -> Dict[str, Any]:
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    out: Dict[str, Any] = {}
    if not os.path.isfile(path):
        return out
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, fn in extractors:
            try:
                out[key] = fn(data)
            except Exception:
                out[key] = None
    except Exception as e:
        out["_error_" + rel] = str(e)
    return out


def render_md(data: Dict[str, Any]) -> str:
    lines = []
    lines.append("# RealAI Puzzle Map (auto-generated)")
    lines.append("")
    lines.append(f"Generated: `{data['meta']['generated_at']}`")
    lines.append("")
    lines.append("This file indexes **existing** scanners and outputs. It does not re-crawl the super-repo.")
    lines.append("")
    lines.append("## Decision order")
    lines.append("")
    for step in data["meta"]["decision_order"]:
        lines.append(f"- {step}")
    lines.append("")
    lines.append("## High-trust facts (if present)")
    lines.append("")
    facts = data.get("facts_from_high_trust") or {}
    if facts:
        for k, v in facts.items():
            lines.append(f"- **{k}:** `{v}`")
    else:
        lines.append("- (no DDS-3 outputs found yet — run polished DDS-3)")
    lines.append("")
    lines.append("## Open these first")
    lines.append("")
    lines.append("| Path | Why |")
    lines.append("|------|-----|")
    for item in data["read_order"]:
        info = file_info(item["path"])
        exists = "yes" if info["exists"] else "missing"
        size = info["size_human"]
        lines.append(f"| `{item['path']}` ({exists}, {size}) | {item['why']} |")
    lines.append("")
    lines.append("## All puzzle pieces")
    lines.append("")
    lines.append("| ID | Gen | Script | Status | Outputs size | Trust | Open first? |")
    lines.append("|----|-----|--------|--------|--------------|-------|-------------|")
    for p in data["pieces"]:
        lines.append(
            f"| `{p['id']}` | {p['generation']} | `{p['script']}` | {p['status']} | "
            f"{p['outputs_total_size_human']} | {p['trust']} | "
            f"{'YES' if p.get('open_first') else ''} |"
        )
    lines.append("")
    lines.append("## Huge artifacts (do not open wholesale)")
    lines.append("")
    if data["huge_artifacts"]:
        for o in data["huge_artifacts"]:
            lines.append(f"- `{o['path']}` — {o['size_human']} — {o['open_advice']}")
    else:
        lines.append("- (none over 50 MB)")
    lines.append("")
    lines.append("## Output detail (present files)")
    lines.append("")
    for p in data["pieces"]:
        present = [o for o in p["outputs_detail"] if o["exists"]]
        if not present:
            continue
        lines.append(f"### {p['id']}")
        lines.append("")
        lines.append(f"Purpose: {p['purpose']}")
        if p.get("note"):
            lines.append(f"Note: {p['note']}")
        lines.append("")
        for o in present:
            lines.append(f"- `{o['path']}` — {o['size_human']} — {o['open_advice']}")
        lines.append("")
    lines.append("## Orphan outputs (not in catalog)")
    lines.append("")
    orphans = data.get("orphan_outputs") or []
    if orphans:
        for o in orphans:
            lines.append(f"- `{o['path']}` — {o['size_human']}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("Narrative guide: `scanners/PUZZLE_MAP.md`")
    lines.append("")
    lines.append("Refresh this file: `python scanners/build_puzzle_map.py`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    data = build()
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(render_md(data))
    print(f"[PUZZLE-MAP] -> {OUT_JSON}")
    print(f"[PUZZLE-MAP] -> {OUT_MD}")
    print(
        f"[PUZZLE-MAP] pieces={data['counts']['catalog_pieces']} "
        f"scripts={data['counts']['scripts_present']} "
        f"open_first={data['counts']['open_first']} "
        f"huge={data['counts']['huge_artifacts']}"
    )
    facts = data.get("facts_from_high_trust") or {}
    if facts:
        print("[PUZZLE-MAP] high-trust facts:", json.dumps(facts, default=str)[:500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
