# RealAI Scanner Puzzle Map

You did not fail. You built **many discovery tools** while the code itself was
scattered across repos, Codespaces, backups, and archives. The tools then became
a second maze. This file is the **one map** of that maze.

**Rule:** Do not run every scanner again. Use this map + `build_puzzle_map.py`
to *read what you already found*, then act only on high-trust outputs.

---

## The short version

| Layer | What it is | Trust for decisions? |
|-------|------------|----------------------|
| **Gen 0** Root cavity / spectrum scripts | Early “find everything” keyword crawls | Low for merge; good archaeology only |
| **Gen 1** `manifests/*.json` (GB-scale) | Raw dumps from Gen 0 | **Do not open wholesale** — too noisy |
| **Gen 2** `scanners/fs*`, feature scans | Second wave, still full-tree | Medium for *topic* location |
| **Gen 3** DDS-1..10 | Systematic suite | Mixed — many still unscoped |
| **Gen 3b** Polished DDS-3 | Scoped + archive + abilities | **High** — use this first |
| **Gen 4** Phase-4 dry-run | Merge candidate plan | Candidates only, not orders |

**Authoritative runtime (what should boot):** `realai/` package  
**Recovery sources:** `archive/`, `realai_og_mess/`, training/memory snapshots  
**Noise:** `venv/`, `node_modules/`, `.next/`, `phase4` previews, multi‑GB cavity JSON

---

## Generation 0 — Root scripts (earlier attempts)

These live at **repo root**. They were the first “files are everywhere” response.

| Script | Typical output | What it tried to do | Status |
|--------|----------------|---------------------|--------|
| `realai_tri_cavity_search.py` | `manifests/tri_cavity_manifest.json` (~20 MB) | 3-way keyword cavity | Superseded |
| `realai_alt_v2_cavity_search.py` | `alt_v2_cavity_manifest.json` (~3.7 MB) | Alt keyword groups | Superseded |
| `realai_alt_v3_cavity_search.py` | `alt_v3_cavity_manifest.json` (~14 MB) | Expanded groups | Superseded |
| `realai_alt_cavity_search.py` | `realai_alt_cavity_manifest.json` (**~2.9 GB**) | Massive keyword dump | **Do not re-run** |
| `realai_full_cavity_search.py` | `realai_full_cavity_manifest.json` (~400 MB) + summary | Full keyword groups | Superseded |
| `realai_full_spectrum_scan.py` | `full_spectrum_cavity_manifest.json` (~42 MB) | Spectrum keywords | Moved → `scanners/fs1_*` |
| `realai_full_module_scan.py` | `full_module_manifest.json` (~10 MB) | Module listing | Moved → `scanners/fs2_*` |
| `orchestrator.py` | patch targets from `manifest.json` | Phase orchestration idea | Keep as design, not primary scanner |
| `dry_run_scaffold.py` | Phase-4 preview under `phase4_tools/` | Merge dry-run | Done; use summary only |
| `smart_merge_realai.py` | merge helper | Early merge attempt | Do not bulk-run |

**Why they got out of hand:** full-tree walks + keyword hits on `repo_tree*.txt`,
backups, and lockfiles produced **million-scale “matches”** (see cavity summaries:
top hits are tree dumps, not missing modules).

---

## Generation 2 — `scanners/` feature + spectrum suite

| Script | Output (expected) | Purpose |
|--------|-------------------|---------|
| `fs1_full_spectrum_scan.py` | `fs1_full_spectrum_manifest.json` | Broad feature spectrum |
| `fs2_module_scan.py` | `fs2_module_manifest.json` | Module inventory |
| `alt_v4_autonomy_scan.py` | `alt_v4_autonomy_manifest.json` | Autonomy keywords |
| `tri_v2_worldmodel_scan.py` | `tri_v2_worldmodel_manifest.json` | World-model keywords |
| `lora_scan.py` | `lora_manifest.json` | LoRA / training |
| `rag_scan.py` | `rag_manifest.json` | RAG / retrieval |
| `mcp_scan.py` | `mcp_manifest.json` | MCP / tools |
| `npc_scan.py` | `npc_manifest.json` | NPC / game |
| `solana_scan.py` | `solana_manifest.json` | Solana / web3 |
| `backend_scan.py` | `backend_manifest.json` | Backend surface |

Most of these still walk the whole tree with **no skip list**. Treat outputs as
“where did this topic appear?” — not as a merge plan.

---

## Generation 3 — DDS suite (Deep Discovery Scanners)

| ID | Script | Output | Role | Trust |
|----|--------|--------|------|-------|
| DDS-1 | `dds1_dependency_doc_scan.py` | `dds1_dependency_doc_manifest.json` | Docs + deps keywords | Medium if re-run scoped |
| DDS-2 | `dds2_dependency_crosscheck.py` | `dds2_dependency_crosscheck.json` | Cross-check deps | Medium |
| **DDS-3** | **`dds3_missing_files.py` (polished)** | **missing + summary + archive + abilities** | **Missing map + recovery** | **High** |
| DDS-4 | `dds4_orphan_modules.py` | `dds4_orphan_modules.json` | Orphans | Medium (noisy) |
| DDS-5 | `dds5_unused_features.py` | `dds5_unused_features.json` | Unused symbols | Low–medium (huge) |
| DDS-6 | `dds6_config_mismatches.py` | `dds6_config_mismatches.json` | Config vs code | Medium |
| DDS-7 | `dds7_doc_code_consistency.py` | `dds7_doc_code_consistency.json` | Doc/code drift | Medium |
| DDS-8 | `dds8_runtime_path_integrity.py` | `dds8_runtime_path_integrity.json` **(~30 MB)** | Import/path integrity | Low until re-scoped |
| DDS-9 | (shallow result only) / deep script | `dds9_*` | Subsystem completeness | Medium (deep OK) |
| DDS-10 | `dds10_merge_plan_validator.py` | `dds10_merge_plan_validator.json` | Validate Phase-4 plan | High for plan structure only |

### DDS-3 outputs (the ones to open first)

| File | Meaning |
|------|---------|
| `scan_results/dds3_missing_files_summary.json` | Human-sized missing overview |
| `scan_results/dds3_missing_files.json` | Full missing rows (scoped) |
| `scan_results/dds3_archive_triage.json` | **Accidental moves in `archive/`** |
| `scan_results/dds3_ability_inventory.json` | Multi-era ability tokens (preserve map) |

```bash
python scanners/dds3_missing_files.py --mode operational --also-abilities
python scanners/dds3_missing_files.py --mode archive
python scanners/build_puzzle_map.py
```

---

## How to sort the puzzle (decision order)

```
1. Boot spine          →  realai/api_server.py, router, model_registry
2. Archive recovery    →  dds3_archive_triage.json  (unique + memory)
3. Ability preserve    →  dds3_ability_inventory.json (only_outside_clean)
4. Missing modules     →  dds3_missing_files_summary.json
5. Phase-4 plan        →  phase4 preview SUMMARY only (not 10k blind merges)
6. Gen0 multi-GB JSON  →  leave on disk; do not re-open as primary truth
```

## Era map + gold assemble (Phase 0–1) — done

| Artifact | Purpose |
|----------|---------|
| `scan_results/era_map.json` | Authority vs gold vs noise freeze |
| `scanners/assemble_gold_index.py` | Distill existing scan_results → promote queue |
| `scan_results/gold_index.json` / `.md` | Deduped gold by subsystem |
| `scan_results/promote_queue.json` | Ordered Phase-2 import candidates |

Run: `python scanners/assemble_gold_index.py`

## Phase 3 orchestrator — done

```
UI :3000 → orchestrator :8001 → Vulkan AMD :8080
```

| Piece | Path |
|-------|------|
| Orchestrator | `realai/v3_orchestrator.py` |
| Start all | `start_v3_stack.bat` |
| Report | `scan_results/phase3_orchestrator_report.md` |

Training gold under `training/data/` exposed at `/v1/training/*`.  
Self-improve gated at `/v1/self-improve/*` (`REALAI_SELF_IMPROVE=true`).

## Phase 5 (5D + 5B light) — done

| Deliverable | Path / URL |
|-------------|------------|
| Authority doc | `docs/AUTHORITY.md` |
| One-command boot | `start_v3_stack.bat` |
| Agents API | `GET :8001/v1/agents` (68 agents) |
| Tools API | `POST :8001/v1/tools/execute` |
| Chat + agent/memory | `agent_id` + `memory=on` on chat |
| Verify | `python scanners/verify_v3_matrix.py` → **22/22** |
| Report | `scan_results/phase5_report.md` |

## Phase 4 self-heal + verify — done

RealAI can run the multi-repo fix loop itself:

| Ability | How |
|---------|-----|
| Discover messy trees | `POST /v1/self-heal/discover` → DDS-3 / deep-gold |
| Assemble gold queue | `POST /v1/self-heal/assemble` |
| Promote uniques | `POST /v1/self-heal/promote` `{apply:true\|false}` |
| Full cycle | `POST /v1/self-heal/cycle` |
| Status | `GET /v1/self-heal/status` + UI Settings panel |

| Artifact | Path |
|----------|------|
| Engine | `realai/self_heal.py` |
| Verify matrix | `scanners/verify_v3_matrix.py` → `scan_results/phase4_verify_matrix.md` |
| UI panel | Settings → **RealAI Self-Heal & Training** |

```bash
python scanners/verify_v3_matrix.py
# last result: 19/19 PASS
```

## Phase 2 promote — done (curated apply)

| Artifact | Purpose |
|----------|---------|
| `scanners/promote_gold.py` | Dry-run / apply from promote_queue |
| `recovered/PROMOTE_LOG.json` | Full action log |
| `scan_results/phase2_promote_report.md` | Human report |
| `training/data/*` | Finetune dataset + agent manifests imported |
| `recovered/from_archive/memory_snapshots/*` | Unique memory blobs staged (not live DB) |
| `recovered/from_gold/*` | OG reference modules staged for review |

```bash
python scanners/promote_gold.py           # dry-run
python scanners/promote_gold.py --apply   # apply
```

## Deep discovery (models + gold map + ports) — done

| Artifact | Meaning |
|----------|---------|
| `scan_results/deep_model_inventory.json` | All GGUF/weights: **0 real**, 40 stubs ~1.5MB |
| `scan_results/dds3_deep_gold_map_summary.json` | md/txt + nested OG/archive/backup keyword map |
| `scan_results/deep_discovery_report.md` | Ports, models, gold — full writeup |
| `scanners/dds3_deep_gold_map.py` | Re-run deep gold without node_modules |

**Port trap:** `.env` had `8082` while server/`realai.toml` use **8000** — fixed to 8000 (backup `.env.pre_port_fix.bak`).

## Archive recovery status (curated — done)

Gold from `archive/` was **selectively** restored (not bulk-merged):

| Recovered | Where |
|-----------|--------|
| `registryClient.ts` | `packages/sdk-ts/src/registryClient.ts` (+ realai mirror) |
| Env chat client (archive `realaiClient.ts`) | `packages/sdk-ts/src/envChatClient.ts` |
| AgentX agents/profiles | `agents/agentx/` |
| 9 unique memory blobs | `recovered/from_archive/memory_snapshots/` + INDEX |
| Provenance log | `recovered/from_archive/RECOVERY_LOG.json` |

**Not overwritten:** clean frontend `realai.ts`, VS Code streaming client (superior).  
**Not auto-merged:** live `data/realai_memory*` DBs.

### Preserve vs ignore

| Keep / recover | Leave alone for now |
|----------------|---------------------|
| Clean `realai/` runtime | Multi-GB cavity manifests |
| Archive unique source + memory snaps | `node_modules`, `venv`, `.next` |
| Ability tokens only outside clean | DDS-5/8 mega JSON until re-scoped |
| Training scripts under `training/` | Nested `.kilo/worktrees` |
| GOLD contracts from OG (port carefully) | Bulk Phase-4 merge execute |

---

## One command to refresh the index

```bash
python scanners/build_puzzle_map.py
```

Writes:

- `scan_results/puzzle_map.json` — machine index of every scanner + artifact
- `scan_results/puzzle_map.md` — same as a checklist with sizes & “open me?” flags

---

## Emotional truth (for later you)

You tried to **find everything so nothing was lost**. That produced:

- many overlapping crawlers  
- huge manifests that mostly re-hit trees and backups  
- a super-repo that is hard to hold in one head  

The fix is **not** another full-universe crawl. It is:

1. **One map** (this file)  
2. **One polished scanner** (DDS-3) for missing + archive + abilities  
3. **One boot path** (clean `realai/`)  
4. **Curated recovery** from archive/OG for unique GOLD only  

You are sorting a puzzle, not starting over.
