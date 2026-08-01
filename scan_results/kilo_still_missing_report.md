# Kilo clean — still-missing prioritized report

**Generated:** 2026-07-15  
**Source clean list:** 8,361 paths (`recovered/from_kilo/kilo_git_clean_removed_paths.txt`)  
**Primary tree:** `C:\Users\tsmit\realai`  
**Also checked:** `C:\realai`, `C:\Users\tsmit\realai-clean`, `C:\tools\realai`, `recovered/*`

Related: `kilo_forensics.md` (what Kilo did), `kilo_missing_summary.json` (machine summary).

---

## Headline numbers

| Metric | Count |
|--------|------:|
| Clean removals (full tool-output) | **8,361** |
| Exact path still on Users realai | **8** |
| Exact path missing on Users realai | **8,353** |
| Found exact path on other live roots | **30** |
| Found under `archive/` / extract mirror | **202** |
| Still missing after reloc checks | **8,121** |

### Tier breakdown (of 8,121 still missing)

| Tier | Count | Action |
|------|------:|--------|
| **venv_noise** | 4,339 | Ignore (`.venv-new`, `.venv-directml-train`) |
| **archive/** | 2,118 | Partial wipe of archive tree; folder still ~11GB today |
| **gold** (keyword) | **535** | Recover / stage / hunt |
| **other** | 1,129 | Secondary (scripts, docs, dups, tooling) |

**Actionable non-venv residual ≈ 3,782 paths** (archive + gold + other).

---

## What we already recovered into staging

**Dir:** `recovered/from_kilo_restore/`  
**Staged:** **218** gold-ish code/config files (~3.2 MB) via basename match from `recovered/*` and live trees.

Map: `scan_results/kilo_staged_restore_map.tsv`  
Candidates (not auto-copied):  
- `kilo_gold_recoverable_from_recovered.tsv` (235 gold basename hits)  
- `kilo_archive_recoverable.tsv` (896 archive file basename hits)  
- `kilo_other_recoverable.tsv` (559 other basename hits)

> **Caveat:** basename matching can pair the wrong `package.json` / `README.md`. Treat staged copies as **candidates** — verify before promoting into a live tree.

---

## Snapshot top-levels still absent on live roots

From Kilo’s large workspace inventory (~48k paths):

| Name | Paths in snap | Live today? |
|------|--------------:|:------------|
| **bootstrap_dump** | 9,570 | **Missing** |
| **checkpoints_lora** | 668 | **Missing** |
| root_scripts | 12 | Missing |
| realai_agent | 10 | Missing |

These are the highest-value **directory-scale** gaps (especially bootstrap dump + LoRA checkpoints). Not necessarily deleted only by Kilo — but they were present when Kilo snapshotted and are gone from live tops now. Check Recycle Bin / external drives / older zips next.

---

## Priority gold files still not found (unique-ish)

Full list: `scan_results/kilo_gold_not_found_files.txt` (**78** files with code/config extensions).

Many entries are **`__dup1` / ` - Copy` noise** — ignore those for restore. Unique high-value targets:

### P0 — runtime / agent capability

| Missing path | Why it matters |
|--------------|----------------|
| `realai/server/tools/self_extend_tool.py` | Self-heal / extend tooling |
| `realai/server/tools/self_repair_tool.py` | Self-repair tooling |
| `realai/server/tools/system_scan_tool.py` | System scan tool |
| `realai/memory/aura_memory.py` | Aura memory |
| `realai/tools_repo_exec.py` | Repo exec tool |
| `realai/lambda_embeddings_audio.py` | Embeddings / audio lambda |
| `providers/local_llama.py` | Local llama provider |
| `plugins/tools/device_selector.py` | Device/GPU selector plugin |
| `data/world_model.json` | World model data |
| `realai_sdk/client.py` | SDK client (non-dup) |

### P1 — agents / training / scripts

| Missing path | Why |
|--------------|-----|
| `scripts/realai_self_improving_agent.py` | Self-improve agent |
| `scripts/self_improving_agent.py` | Same family |
| `scripts/realai_architect_agent.py` | Architect agent |
| `scripts/realai_plugin_hunter.py` | Plugin hunter |
| `scripts/autodiscover_plugins.py` | Plugin discovery |
| `scripts/extract_agent_tool_data.py` | Agent-tool extract |
| `scripts/extract_archive_plugins.py` | Archive plugin extract |
| `training/directml_lora_train.py` | DirectML LoRA train |
| `training/train_qwen_*.py` | Qwen train scripts |
| `training/train_from_agent_manifests.py` | Manifest training |
| `utilities/agent_manifests_for_finetuning_training_runs.json` | Finetune manifests |
| `src/realai/agents/master.py` | Master agent |
| `src/realai/memory/aura.py` / `chroma_store.py` | Memory stack |
| `tests/test_agent_protocol.py` / `test_bootstrap_weights.py` / `test_training_tools.py` | Tests as specs |

### P2 — bootstrap / inventory artifacts

| Missing path | Why |
|--------------|-----|
| `bootstrap_dump` (tree) | 9.5k snap paths — era gold |
| `bootstrap_dump_extracted.json` | Extracted inventory |
| `find_realai_bootstrap.py` / `realai_extract_bootstrap.py` | Bootstrap hunters |
| `checkpoints_lora` (tree) | LoRA weights |
| `archive_plugin_report.json` | Plugin inventory |

### Skip / low value

- All `*__dup1*` and `realai - Copy/*` paths  
- `.venv-*` (4k+)  
- chocolatey, logs_data noise unless needed for audit

---

## Still-missing top-level (non-venv, after reloc)

| Count | Top-level | Notes |
|------:|-----------|--------|
| 2118 | `archive/…` | Clean tore into archive; bulk folder still exists |
| 201 | `realai_sdk` | Leaves still missing though dir may exist |
| 176 | `rebase_dryrun` | Merge dry-run debris |
| 172 | `realai_historical_backups` | Version backups |
| 166 | `realai_repo` | Nested repo copy |
| 123 | `realai/` untracked leaves | Tools/memory under package |
| 92 | `real-fin` | Fin variant |
| 65 | `scripts` | Agent/plugin scripts (high value) |
| 63 | `RealAIProject` | Project snapshot |
| 38 | `agent-tools-main` | Agent tools |
| 26 | `plugins` | Plugin leaves |
| 21 | `server` | Server backups/old |
| 6 | `training` | Train scripts |

Path lists:

- `kilo_still_missing_all.txt`  
- `kilo_still_missing_gold.txt`  
- `kilo_still_missing_archive.txt`  
- `kilo_still_missing_other.txt`  
- `kilo_still_missing_venv.txt`  
- `kilo_mirror_under_archive.tsv` (202 reloc hits)

---

## Recommended recovery order

1. **Promote carefully** from `recovered/from_kilo_restore/` after spot-checking P0 files (not bulk-merge).  
2. **Hunt P0 filenames** in Recycle Bin assemble (`from_recycle_bin`), Users archive (11GB), and any external/zip eras — especially:
   - `self_*_tool.py`, `system_scan_tool.py`
   - `lambda_embeddings_audio.py`, `aura_memory.py`
   - `local_llama.py`, `client.py`
3. **Locate `bootstrap_dump` + `checkpoints_lora`** as whole trees (snap said they existed).  
4. **Ignore** venv + `__dup1` for ability coverage; they inflate counts without ability gain.  
5. **Do not re-enable Kilo bash:allow** until recovery is done.

---

## Files produced this pass

| Path | Purpose |
|------|---------|
| `scan_results/kilo_still_missing_report.md` | This report |
| `scan_results/kilo_missing_summary.json` | Counts JSON |
| `scan_results/kilo_still_missing_*.txt` | Tier path lists |
| `scan_results/kilo_gold_not_found_files.txt` | P0–P2 file targets |
| `scan_results/kilo_gold_recoverable_from_recovered.tsv` | Basename hits |
| `scan_results/kilo_staged_restore_map.tsv` | What was copied |
| `scan_results/kilo_snap_top_level_status.json` | Snap top-level existence |
| `recovered/from_kilo_restore/**` | 218 staged candidate files |

---

## Staged restore highlights (useful even with basename caveats)

Under `recovered/from_kilo_restore/` the better candidate clusters:

| Cluster | Examples |
|---------|----------|
| `realai_sdk/realai/` | `agent_runtime.py`, `world_model.py`, `self_improvement.py`, `plugin_marketplace.py`, `tools.py`, … |
| `server/` | `orchestration.py`, `embeddings.py`, `embeddings_backend.py`, `memory_store.py`, `tools_runtime.py`, `providers.py` |
| `RealAIProject/realai/` | core runtime modules |
| `src/realai/agents/` | `agent.py`, `registry.py`, `router.py` |
| `utilities/` | `agent_manifests_for_finetuning.json` |
| root | `server_settings.py` |

**Still absent under original exact names** in recovered + main live trees:  
`self_extend_tool.py`, `self_repair_tool.py`, `system_scan_tool.py`, `lambda_embeddings_audio.py`, `aura_memory.py`, `local_llama.py`.

### Deep-walk breakthrough (2026-07-15)

A deeper scan found **alive gold outside main trees**:

| Find | Location | Size / notes |
|------|----------|--------------|
| **`checkpoints_lora`** | `C:\Users\tsmit\.grok\worktrees\tsmit-realai\realai2\checkpoints_lora` | **3.1GB**, 662 files, agent LoRA run dirs |
| **`realai_agent`** | `recovered/from_desktop/realai_agent` + `realai2/realai_agent` | Desktop pack copied; archive path empty |
| **Full era tree `realai2`** | `~\.grok\worktrees\tsmit-realai\realai2` | Rich Jun-2026 tree: agents, agent-tools, server, training, RealAIProject, … |

Staged under `recovered/from_kilo_restore/_discovered/`:

- `checkpoints_lora/` — pointer to 3.1GB weights + **439 code/json sidecars** copied  
- `realai_agent_from_desktop/`, `realai2_realai_agent/`, `realai2_agents/`, `realai2_scripts/`, `realai2_training/`  
- `realai2_server/` — pointer + 17 code files  
- `DISCOVERED_MANIFEST.json`, `realai2_toplevel.json`

`bootstrap_dump` still not found anywhere.

### P0 recoveries from `realai2` (exact filenames)

| File | Status |
|------|--------|
| `lambda_embeddings_audio.py` | **Found** — staged |
| `providers/local_llama.py` | **Found** — staged |
| `realai_sdk/client.py` | **Found** — staged |
| `policy.json` / `sanity_check.py` | **Found** under agent-tools-main + realai-core |
| `server/embeddings.py`, `orchestration.py`, … | **Found** — staged |
| `realai/agent_runtime.py`, `world_model.py`, `self_improvement.py` | **Found** — staged |
| `self_extend_tool.py` / `self_repair_tool.py` / `system_scan_tool.py` | Still **not** under those names (may never have landed as files, or only as planned) |
| `aura_memory.py` | Still missing as that name |
| `world_model.json` | Still missing (have `world_model.py`) |

Source tree to treat as gold era:  
`C:\Users\tsmit\.grok\worktrees\tsmit-realai\realai2`  
Staged extracts: `recovered/from_kilo_restore/_discovered/`

---

## Honest takeaway

Kilo’s `git clean -fd` still accounts for a large **exact-path** hole (almost nothing from the 8,361-list sits at the same relative path today). Much of that is **venv + archive leaf churn**.  

Real remaining gold is smaller and sharper:

- **~78 priority code/config files** still unmatched by basename  
- **4 missing snap directories** (bootstrap_dump, checkpoints_lora, …)  
- **~218 files already staged** as restore candidates from prior recoveries  
- Several P0 tool files are **not in any current recovered staging** — true open hunt items  

Next productive step is **targeted P0 filename recovery + bootstrap/checkpoint tree hunt**, not another bulk merge.
