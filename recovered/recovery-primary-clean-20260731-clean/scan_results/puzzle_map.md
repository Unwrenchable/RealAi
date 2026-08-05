# RealAI Puzzle Map (auto-generated)

Generated: `2026-07-13T16:53:10.048760+00:00`

This file indexes **existing** scanners and outputs. It does not re-crawl the super-repo.

## Decision order

- 1. Boot clean realai/ package
- 2. dds3_archive_triage recover candidates
- 3. dds3_ability_inventory only_outside_clean
- 4. dds3_missing_files_summary
- 5. Phase-4 summary counts (not bulk merge)
- 6. Ignore multi-GB cavity JSON as primary truth

## High-trust facts (if present)

- **unique_missing:** `127`
- **files_scanned:** `569`
- **by_era:** `{'clean_runtime': 274, 'training': 9, 'other': 52, 'archive': 3}`
- **archive_recover_candidates:** `63`
- **archive_only_in_archive:** `15`
- **archive_memory_snapshots:** `24`
- **ability_tokens:** `119`
- **ability_only_outside_clean:** `36`
- **ability_multi_era:** `83`

## Open these first

| Path | Why |
|------|-----|
| `scanners/PUZZLE_MAP.md` (yes, 8.1 KB) | Narrative map of every generation |
| `scan_results/puzzle_map.md` (yes, 0 B) | Auto checklist with file sizes |
| `scan_results/dds3_missing_files_summary.json` (yes, 9.6 KB) | Scoped missing overview |
| `scan_results/dds3_archive_triage.json` (yes, 40.9 KB) | Accidental moves in archive/ |
| `scan_results/dds3_ability_inventory.json` (yes, 48.1 KB) | Multi-era abilities to preserve |
| `phase4_tools/plan_phase4_preview/phase4_preview_summary.txt` (yes, 322 B) | Merge counts only |
| `realai/api_server.py` (yes, 56.3 KB) | Boot spine (clean runtime) |

## All puzzle pieces

| ID | Gen | Script | Status | Outputs size | Trust | Open first? |
|----|-----|--------|--------|--------------|-------|-------------|
| `gen0-tri-cavity` | 0 | `realai_tri_cavity_search.py` | has_output | 19.6 MB | archaeology |  |
| `gen0-alt-v2` | 0 | `realai_alt_v2_cavity_search.py` | has_output | 3.6 MB | archaeology |  |
| `gen0-alt-v3` | 0 | `realai_alt_v3_cavity_search.py` | has_output | 13.4 MB | archaeology |  |
| `gen0-alt-cavity` | 0 | `realai_alt_cavity_search.py` | done_do_not_rerun | 2.7 GB | noise_if_huge |  |
| `gen0-full-cavity` | 0 | `realai_full_cavity_search.py` | done_do_not_rerun | 384.8 MB | archaeology |  |
| `gen0-full-spectrum` | 0 | `realai_full_spectrum_scan.py` | has_output | 39.7 MB | archaeology |  |
| `gen0-full-module` | 0 | `realai_full_module_scan.py` | has_output | 9.4 MB | archaeology |  |
| `gen0-orchestrator` | 0 | `orchestrator.py` | script_only_no_output_yet | — | medium |  |
| `gen0-dry-run` | 0 | `dry_run_scaffold.py` | ready_open_first | 6.4 MB | medium | YES |
| `gen0-smart-merge` | 0 | `smart_merge_realai.py` | script_only_no_output_yet | — | low |  |
| `fs1` | 2 | `scanners/fs1_full_spectrum_scan.py` | script_only_no_output_yet | — | medium |  |
| `fs2` | 2 | `scanners/fs2_module_scan.py` | script_only_no_output_yet | — | medium |  |
| `alt-v4` | 2 | `scanners/alt_v4_autonomy_scan.py` | script_only_no_output_yet | — | medium |  |
| `tri-v2` | 2 | `scanners/tri_v2_worldmodel_scan.py` | script_only_no_output_yet | — | medium |  |
| `lora` | 2 | `scanners/lora_scan.py` | script_only_no_output_yet | — | medium |  |
| `rag` | 2 | `scanners/rag_scan.py` | script_only_no_output_yet | — | medium |  |
| `mcp` | 2 | `scanners/mcp_scan.py` | script_only_no_output_yet | — | medium |  |
| `npc` | 2 | `scanners/npc_scan.py` | script_only_no_output_yet | — | medium |  |
| `solana` | 2 | `scanners/solana_scan.py` | script_only_no_output_yet | — | medium |  |
| `backend` | 2 | `scanners/backend_scan.py` | script_only_no_output_yet | — | medium |  |
| `dds1` | 3 | `scanners/dds1_dependency_doc_scan.py` | script_only_no_output_yet | — | medium |  |
| `dds2` | 3 | `scanners/dds2_dependency_crosscheck.py` | script_only_no_output_yet | — | medium |  |
| `dds3` | 3 | `scanners/dds3_missing_files.py` | ready_open_first | 200.6 KB | high | YES |
| `dds4` | 3 | `scanners/dds4_orphan_modules.py` | has_output | 223.4 KB | medium |  |
| `dds5` | 3 | `scanners/dds5_unused_features.py` | has_output | 2.0 MB | low |  |
| `dds6` | 3 | `scanners/dds6_config_mismatches.py` | has_output | 722 B | medium |  |
| `dds7` | 3 | `scanners/dds7_doc_code_consistency.py` | has_output | 1.8 MB | medium |  |
| `dds8` | 3 | `scanners/dds8_runtime_path_integrity.py` | has_output | 29.2 MB | low |  |
| `dds9-deep` | 3 | `scanners/dds9_subsystem_completeness_deep.py` | has_output | 81.8 KB | medium |  |
| `dds10` | 3 | `scanners/dds10_merge_plan_validator.py` | ready_open_first | 1.8 MB | high | YES |
| `puzzle-map` | 4 | `scanners/build_puzzle_map.py` | ready_open_first | 44.7 KB | high | YES |

## Huge artifacts (do not open wholesale)

- `manifests/realai_alt_cavity_manifest.json` — 2.7 GB — TOO_LARGE_for_editor — use summary only or jq filters
- `manifests/realai_full_cavity_manifest.json` — 384.8 MB — TOO_LARGE_for_editor — use summary only or jq filters

## Output detail (present files)

### gen0-tri-cavity

Purpose: Early 3-group keyword cavity search

- `manifests/tri_cavity_manifest.json` — 19.6 MB — Large — open summary/top keys only

### gen0-alt-v2

Purpose: Alt keyword cavity v2

- `manifests/alt_v2_cavity_manifest.json` — 3.6 MB — OK if needed

### gen0-alt-v3

Purpose: Alt keyword cavity v3

- `manifests/alt_v3_cavity_manifest.json` — 13.4 MB — Large — open summary/top keys only

### gen0-alt-cavity

Purpose: Massive keyword dump (multi-GB risk)

- `manifests/realai_alt_cavity_manifest.json` — 2.7 GB — TOO_LARGE_for_editor — use summary only or jq filters
- `realai_alt_cavity_summary.txt` — 4.4 KB — Safe to open

### gen0-full-cavity

Purpose: Full keyword cavity + group summaries

- `manifests/realai_full_cavity_manifest.json` — 384.8 MB — TOO_LARGE_for_editor — use summary only or jq filters
- `realai_full_cavity_summary.txt` — 4.3 KB — Safe to open

### gen0-full-spectrum

Purpose: Spectrum keyword scan (root copy)

- `manifests/full_spectrum_cavity_manifest.json` — 39.7 MB — Large — open summary/top keys only

### gen0-full-module

Purpose: Module listing (root copy)

- `manifests/full_module_manifest.json` — 9.4 MB — Large — open summary/top keys only

### gen0-dry-run

Purpose: Phase-4 merge dry-run preview
Note: Use SUMMARY counts only; do not execute bulk merge yet

- `phase4_tools/plan_phase4_preview/phase4_preview_summary.txt` — 322 B — Safe to open
- `phase4_tools/plan_phase4_preview/phase4_preview.json` — 6.4 MB — Large — open summary/top keys only

### dds3

Purpose: Scoped missing map + archive triage + ability inventory
Note: Primary scanner after polish. Run operational + archive + abilities.

- `scan_results/dds3_missing_files.json` — 102.1 KB — Safe to open (primary)
- `scan_results/dds3_missing_files_summary.json` — 9.6 KB — Safe to open
- `scan_results/dds3_archive_triage.json` — 40.9 KB — Safe to open
- `scan_results/dds3_ability_inventory.json` — 48.1 KB — Safe to open (primary)

### dds4

Purpose: Orphan modules

- `scan_results/dds4_orphan_modules.json` — 223.4 KB — OK if needed

### dds5

Purpose: Unused feature symbols (often huge/noisy)

- `scan_results/dds5_unused_features.json` — 2.0 MB — OK if needed

### dds6

Purpose: Config mismatches

- `scan_results/dds6_config_mismatches.json` — 722 B — OK if needed

### dds7

Purpose: Doc vs code consistency

- `scan_results/dds7_doc_code_consistency.json` — 1.8 MB — OK if needed

### dds8

Purpose: Runtime path integrity (re-scope before trusting)

- `scan_results/dds8_runtime_path_integrity.json` — 29.2 MB — Large — open summary/top keys only

### dds9-deep

Purpose: Subsystem completeness

- `scan_results/dds9_subsystem_completeness_deep.json` — 80.9 KB — OK if needed
- `scan_results/dds9_subsystem_completeness.json` — 930 B — OK if needed

### dds10

Purpose: Validate Phase-4 merge plan structure
Note: Validates plan files only; does not walk product code

- `scan_results/dds10_merge_plan_validator.json` — 1.8 MB — OK if needed

### puzzle-map

Purpose: This index — consolidates the puzzle without re-crawling

- `scan_results/puzzle_map.json` — 28.2 KB — Safe to open
- `scan_results/puzzle_map.md` — 8.4 KB — Safe to open
- `scanners/PUZZLE_MAP.md` — 8.1 KB — Safe to open

## Orphan outputs (not in catalog)

- `scan_results/archive_recovery_log.json` — 10.2 KB

---

Narrative guide: `scanners/PUZZLE_MAP.md`

Refresh this file: `python scanners/build_puzzle_map.py`
