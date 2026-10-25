# Local shelf inventory — 2026-09-25 (PT)

Read-only inventory of external gold + recovered/imports shelves for unique RealAI product code that may have been wrongly archived. **No copy/merge onto live. No git add/commit/push.**

Machine: `3d3d81a2-235f-4f88-a155-c58369f7a702`

---

## 1. Top-level layout

### `C:\RealAI-gold` (external gold shelf)

| top-level | ~files | ~size | nested `.git` |
|-----------|-------:|------:|:-------------:|
| abilities | 14 | 61 KB | no |
| agents | 37 | 212 KB | no |
| apps | 445 | 4.3 MB | no |
| frontend | 4 | 16 KB | no |
| **orphans** | **3489** | **63.6 MB** | no |
| packages | 2 | 5 KB | no |
| providers | 6 | 3 KB | no |
| **realai** | **1230** | **38.1 MB** | no |
| scripts | 21 | 151 KB | no |

- Root itself has **no** `.git`.
- `orphans/_parked` dominates (~62 MB / 3231 files); biggest parked bucket is `2026-08-30-pkg-clean` (~61 MB, includes `_venv-unwind` HF noise).
- `realai/plugins` is mostly **path-encoded `C__realai_*` dumps** (~712 files / 2.9 MB) — not product source.
- `realai/memory` ~13 MB; `realai/orchestrator-default-run` ~12 MB; `realai/deep_nests` ~8 MB.

`apps/` shallow: `api`, `dashboard` (noise icon dump), `frontend` (Next stubs), `vscode` (many `@types` + `C__*` JSON noise + some real `chatPanel.*` / `console-dev.js`).

### `C:\RealAI-clean\recovered`

| entry | ~files | ~size | notes |
|-------|-------:|------:|-------|
| README.txt | — | 314 B | placeholder; historical archive on `D:\RealAI-archive\recovered` |
| CURATED_PROMOTE_LOG.json | — | 4.9 KB | 2026-09-24 promote; **copied/wrote 0**, 10 skipped (dest exists / keep_live) |
| EXTERNAL_IMPORT_LOG.json | — | 6.5 KB | dry-run import map; many external srcs missing |
| **from_d_roots/** | **3762** | **~40.3 GB** | D: roots import — **huge dumps** |
| realai-import-20260919/ | 15 | 120 KB | small import slice (`api_server.py`, `cli`, `plugins`, `v3_orchestrator.py`, …) |

No nested `.git`.

#### `from_d_roots/` breakdown

| dir | ~files | ~size | flag |
|-----|-------:|------:|------|
| realai | 24 | 0.5 MB | small |
| realai_agent | 10 | 60 KB | small |
| realai_api | 7 | 7 KB | tiny |
| realai_api_atomicfizz | 1 | 120 B | stub |
| **realai_archive** | 1500 | **300 MB** | `_quarantine` ~198 MB + `recovered` ~117 MB |
| **realai_archives** | 1500 | **~40.0 GB** | **NOISE: tar.gz + giant_hold** |
| realai_cli | 8 | 13 KB | small |
| realai_copy | 160 | 1.1 MB | copy tree |
| realai_design_system | 44 | 37 KB | small |
| realai_historical_backups | 488 | 6.8 MB | version dumps |
| realai_orchestration | 7 | 36 KB | small |
| realai_sdk | 8 | 129 KB | small |
| tools_realai | 5 | 1 KB | tiny |

**`realai_archives/users-tsmit-realai` (~42.1 GB)** is almost entirely:
- `.vscode/realai_giant_hold/` (~27.1 GB): `realai-clean-20260726-source-only` (~14.7 GB), `unification-snapshots` (~9.1 GB), `local-recovery-primary-clean-20260731` (~3.3 GB)
- `realai-core.tar.gz` + `.part-aa/ab/ac` (~14.7 GB combined)

Treat as **archive blobs / giant holds**, not promote candidates.

### `C:\RealAI-clean\imports` (exists)

| entry | notes |
|-------|-------|
| README.txt | same placeholder pattern → historical on `D:\RealAI-archive\imports` |
| **promoted/** | 4 files / ~14 KB: `local_models.py`, `self/`, `__init__.py` |

No nested `.git`. Thin local stub only.

---

## 2. Interesting Python/JS/HTML candidates (~40)

Prioritized hive / bridge / console / plugins / abilities / organs / orchestrator / craft / self_heal. Excluded `C__*` path dumps, `node_modules`, HF `*bridgetower*`, and `.before` (listed under noise).

| size | path |
|-----:|------|
| 139681 | `C:\RealAI-gold\orphans\_parked\2026-09-08-realai-gateway\v3_orchestrator.py` |
| 136346 | `C:\RealAI-gold\orphans\_parked\2026-09-08-xtts-console\v3_orchestrator.py` |
| 134482 | `C:\RealAI-gold\orphans\_parked\2026-09-07-orch2\v3_orchestrator.py` |
| 130497 | `C:\RealAI-gold\orphans\_parked\2026-09-07-orch2\craft.py` |
| 124350 | `C:\RealAI-clean\recovered\from_d_roots\realai_archive\_quarantine\cli\craft.py` |
| 69520 | `C:\RealAI-gold\orphans\realai\v3_orchestrator.py` *(twin in quarantine)* |
| 58691 | `C:\RealAI-gold\orphans\realai\v3_runtime_bridge.py` |
| 58624 | `C:\RealAI-gold\orphans\realai\orchestration\v3_orchestrator.py` |
| 52596 | `C:\RealAI-gold\orphans\delta_candidates\core\realai\core\orchestration\v3_orchestrator.py` |
| 50371 | `C:\RealAI-gold\orphans\realai\ability_catalog.py` |
| 49127 | `C:\RealAI-gold\orphans\main-realai\realai\v3_orchestrator.py` |
| 49127 | `...\realai_archive\_quarantine\orchestrators\nested_realai_v3_orchestrator.py` |
| 45383 | `C:\RealAI-gold\realai\agent_tools_gold\dashboard.py` |
| 33825 | `C:\RealAI-gold\orphans\main-realai\realai\ability_catalog.py` |
| 23234 | `...\realai_archive\_quarantine\self_heal.py` |
| 20966 | `C:\RealAI-gold\abilities\...\nest_orchestrators.py` |
| 18085 | `C:\RealAI-gold\orphans\main-realai\realai\v3_runtime_bridge.py` |
| 17549 | `...\realai_archive\_quarantine\agents\self_heal.py` (and several renamed twins) |
| 16241 | `...\realai_archive\_quarantine\core\repo_organizer.py` |
| 15055 | `C:\RealAI-gold\realai\realai\v3_orchestrator.py` |
| 14668 | `C:\RealAI-clean\recovered\realai-import-20260919\v3_orchestrator.py` |
| 12419 | `...\quarantine\orchestrators\orchestrator_router.py` |
| 11412 | `...\quarantine\orchestrators\orchestrator_self_improvement.py` |
| 10069 | `...\quarantine\realai_hive_orchestrator.py` |
| 9375 | `...\quarantine\plugin_marketplace.py` |
| 9062 | `...\quarantine\realai_self_healing_core.py` |
| 6539 | `...\quarantine\self_heal_loop.py` |
| 6491 | `C:\RealAI-gold\apps\vscode\console-dev.js` |
| 3866 | `C:\RealAI-gold\orphans\realai\orchestration\hive_router.py` |
| 3750 | `...\quarantine\orchestration\hive_router.py` |
| 3482 | `...\quarantine\abilities\hive_memory.py` |
| 2842 | `C:\RealAI-gold\realai\modules\organs\evolution\synthetic_organ_generator.py` |
| 2823 | `C:\RealAI-gold\realai\modules\organs\body\device_walker_organ.py` |
| 2651 | `C:\RealAI-gold\orphans\_parked\2026-09-07-universe\cli-hive-commands-world.py` |
| 2541 | `C:\RealAI-gold\realai\modules\organs\hive.py` |
| 2132 | `C:\RealAI-gold\orphans\grok-worktrees\realai2\realai_plugin_hunter.py` |
| 1808 | `...\quarantine\abilities\organs_hive.py` |
| 1512 | `C:\RealAI-gold\abilities\...\ability_matrix.py` |
| 1312 | `...\quarantine\hive_orchestrator.py` |
| 881 | `C:\RealAI-gold\realai\realai-core\console\console.js` |
| 736 | `...\quarantine\adapters\organs.py` |

Also note parked UI/gateway slices worth a later basename+hash pass (not all listed above):
- `orphans\_parked\2026-09-08-hive-agents-ui\` (mostly `.before` — do not promote)
- `orphans\_parked\2026-09-08-realai-gateway\`
- `orphans\_parked\2026-09-08-xtts-console\`

---

## 3. Existing shelf / promote docs under `C:\RealAI-clean\docs`

Already scored these shelves (do not re-promote blindly):

| doc | date | takeaway |
|-----|------|----------|
| **`SHELF_CONTENT_DELTA.md`** (4894 B) | 2026-09-21 | Gold + backup scanned (cap 400 .py/shelf). UNIQUE 136 raw → **~6 clean UNIQUE / 19 REVIEW** after junk filter. **PROMOTED: 0**. Explicitly parks orphans `.before`, hive world CLI, BridgeTower HF config; hive_router / organs / ability_matrix / rackup_coach marked REVIEW (live already has authority or collision). |
| **`QUARANTINE_CONTENT_DELTA.md`** (2926 B) | 2026-09-21 | Basename+sha vs live. REVIEW 3 (`ability_catalog`, organs `base`, `build_datasets`) — **none promoted**. |
| **`QUARANTINE_DELTA.md`** (15097 B) | 2026-09-21 | 10 CANDIDATE unique plugin___init___* / marketplace / sample_plugin basenames; 138 STAY. |
| **`REALAI_PKG_CONTENT_DELTA.md`** (21064 B) | (pkg vs product) | fusion-ui / apps API DIFF-REVIEW; GOLD never parked. |

Promote logs on shelf:
- `recovered/CURATED_PROMOTE_LOG.json` — applied 2026-09-24 ~12:08 PT (UTC 19:08); **0 files copied**.
- `recovered/EXTERNAL_IMPORT_LOG.json` — dry-run only.

**This inventory does not supersede those deltas**; it maps where remaining large twins / parked orch+bridge+craft still sit.

---

## 4. Obvious noise (do not promote)

| noise | where | why |
|-------|-------|-----|
| **Giant holds / tar dumps** | `recovered\from_d_roots\realai_archives\users-tsmit-realai` (~42 GB) | `.vscode\realai_giant_hold` (~27 GB) + `realai-core.tar.gz` (+parts) |
| **`C__realai_*` path-encoded dumps** | gold `realai\plugins`, gold `apps\vscode\*`, quarantine `plugins\` | flattened node_modules / venv / eslint-plugin debris |
| **`.before` copies** (4 on gold) | `_parked\2026-09-08-hive-agents-ui\`, `multi-agent-liveexec\`, `multi-agent-worker\` | already flagged UNIQUE-but-do-not-promote in SHELF_CONTENT_DELTA |
| **HF BridgeTower / modeling_*** | `_parked\2026-08-30-pkg-clean\_venv-unwind\` | third-party, not product |
| **`node_modules`** | not present as live dirs on these three roots (pruned); encoded copies remain under `C__*` names | treat as NOISE |
| **Huge files (>50 MB)** | 20 under recovered (archives only); 0 under gold/imports | blobs |
| **Duplicate renamed twins** | quarantine `realai__self_heal.py` / `self_heal.py` / `agents\self_heal.py` same size 17549 | copy churn |
| **Placeholder README shelves** | recovered + imports | point at `D:\RealAI-archive\...`; local trees are partial |

---

## 5. Quick judgment (inventory only)

- **Best shelf for unique product code hunting:** `C:\RealAI-gold\orphans\_parked\2026-09-0{7,8}-*` (gateway / xtts-console / orch2 craft / universe hive CLI) and `C:\RealAI-gold\orphans\realai\` + `main-realai\` bridges/orchestrators — but SHELF_CONTENT_DELTA already scored many as REVIEW/parked.
- **Largest volume is not code:** `from_d_roots\realai_archives` (~40 GB) is holds/tarballs — skip for promote.
- **Quarantine under `realai_archive\_quarantine`** (~198 MB) is the densest *code* twin pile; content-delta docs already said promote 0.
- **`imports\promoted`** is tiny (already-promoted crumbs only).

No files were copied, merged, or git-touched.
