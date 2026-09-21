# Quarantine same-name content delta (2026-09-21)

Compare quarantine `.py` vs live gold by **basename + sha256**.
Gold roots: `realai/orchestration`, `realai/plugins`, `realai/core`, `modules/organs`, `abilities`.
Skipped: `__init__.py`, `plugin___init___N.py`, node_modules, jsonl.
Cap: first 80 DIFF pairs.

## Counts

| status | count |
|--------|------:|
| IDENTICAL | 74 |
| NOISE (DIFF, no added top-level defs) | 46 |
| REVIEW (DIFF with added defs; not promoted) | 3 |
| PROMOTED | 0 |
| DIFF examined (capped) | 49 |

## Runtime note

`:8001/health` refused connection this pass (stack down). Did not start a server.

## REVIEW (symbol names) — no promote

| basename | live_path | q_path | status | added_defs |
|----------|-----------|--------|--------|------------|
| `ability_catalog.py` | `realai/plugins/ability_catalog.py` | `_quarantine/twins_20260921/realai__plugins__plugins/ability_catalog.py` | REVIEW | `_enrich_status_from_disk`, `_token_keywords_from_inventory`, `_utc`, `build_catalog`, `coverage_summary`, `emit_training_samples`, `external_scan_roots`, `first_existing`, `learn_keywords_from_scans`, `load_ability_inventory`, `load_era_map`, `load_learned_keywords`, `main`, `path_exists`, `save_catalog`, `scan_tools_cli_surface`, `to_wsl_or_native` |
| `base.py` | `realai/plugins/tools/base.py` | `_quarantine/twins_20260921_b/realai__imports/external/C_realai_modules/organs/base.py` | REVIEW | `Organ`, `OrganContext`, `OrganResult` |
| `build_datasets.py` | `realai/plugins/build_datasets.py` | `_quarantine/twins_20260921/realai__grok_export_realai/RealAI-clean/training/build_datasets.py` | REVIEW | `build_dataset_bundle`, `main` |

### Why not promoted

- **`ability_catalog.py`** — Live plugins copy is a shim re-exporting `realai.ability_catalog`. Symbols (`build_catalog`, `coverage_summary`, `load_ability_inventory`, …) are already importable. Quarantine is a full dump twin; do not replace the shim.
- **`base.py`** — Basename collision across packages (organs vs `plugins/tools`). `Organ` / `OrganContext` / `OrganResult` already live in `modules/organs/base.py`.
- **`build_datasets.py`** — Paired to `plugins/build_datasets.py`, but `build_dataset_bundle` already exists in `realai/training/build_datasets.py`. Quarantine file is a smaller alternate API; do not overwrite the plugins module.

## Sample NOISE

46 DIFF pairs with empty `added_defs` (whitespace / copy churn / same API surface). Examples include many organ and plugin twins where top-level `class`/`def` names already match live. Full listing omitted; re-run hash-pair scan if needed.

## Promote decision

**Promoted: none** (0 symbols, 0 files). No patch met strict rules.

## Smokes (post-pass)

- `modules.organs.hive_status` → organ_count 45, complete True
- `realai.hive.register_plugins` → sample_plugin / rackup-coach / atomicfizz ok
- `python -m realai.v3_orchestrator --help` → usage ok
