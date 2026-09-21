# Shelf content delta (backup + gold) — 2026-09-21

Shelves are **read-only libraries**. No xcopy onto live. Quarantine twins not rescanned.
Live gold roots: orchestration, plugins, core, modules/organs, abilities, apps/vscode, frontend.
Scan: preferred paths (organs/plugins/orchestration/abilities/hive/self_heal/rackup), cap **400 .py per shelf**.

## Shelf inventory (top-level ~py counts)

### backup (`C:\RealAI-clean-backup`)

| top-level | ~py |
|-----------|----:|
| abilities | 64 |
| adapters | 7 |
| agent_tools | 50 |
| agents | 9 |
| api | 2 |
| apps | 259 |
| aura | 9 |
| autopilot | 0 |
| benchmarks | 9 |
| billing | 1 |
| core | 122 |
| imports | 360 |
| modules | 116 |
| plugins | 216 |
| realai | 2365 |
| recovered | 96 |
| scripts | 88 |
| server | 17 |
| tests | 19 |
| tools | 16 |
| training | 14 |
| *(other tops ≤9)* | — |

### gold (`C:\RealAI-gold`)

| top-level | ~py |
|-----------|----:|
| abilities | 14 |
| agents | 12 |
| apps | 11 |
| frontend | 0 |
| orphans | 3488 |
| packages | 2 |
| providers | 2 |
| realai | 292 |
| scripts | 16 |

Both shelf roots **exist**.

## Counts (raw scan, 400/shelf)

| status | count |
|--------|------:|
| IDENTICAL | 218 |
| NOISE | 154 |
| REVIEW | 19 |
| UNIQUE | 136 |
| SKIP_NONDOMAIN | 273 |
| PROMOTED | 0 |

After junk filter (venv / site-packages / `C__*` dumps): most UNIQUE rows are third-party trash; ~6 clean UNIQUE, 19 clean REVIEW.

## REVIEW + UNIQUE (clean)

| shelf | path | basename | live_path | status | added_defs | note |
|-------|------|----------|-----------|--------|------------|------|
| backup | `adapters/organs.py` | `organs.py` | | UNIQUE | `invoke_organ`, `list_all_organs`, `organs_status` | Already on live as `realai/adapters/organs.py` (adapters outside gold-root index). |
| gold | `abilities/.../ability_matrix.py` | `ability_matrix.py` | | UNIQUE | `describe`, `load_matrix` | Reconstructed stub; also `realai/scripts/verify_matrix.py`. REVIEW only. |
| gold | `orphans/.../cli-hive-commands-world.py` | `cli-hive-commands-world.py` | | UNIQUE | `world_*` | Parked orphans — do not promote. |
| gold | `orphans/.../agent_activity.before.py` | `agent_activity.before.py` | | UNIQUE | `EventBus`, … | Parked `.before` — do not promote. |
| gold | `orphans/.../v3_orchestrator.before-*.py` | `v3_orchestrator.before-*.py` | | UNIQUE | many | Parked `.before` — do not promote. |
| gold | `orphans/.../configuration_bridgetower.py` | `configuration_bridgetower.py` | | UNIQUE | `BridgeTower*` | HF config orphan — skip. |
| backup | `core|realai/orchestration/hive_router.py` | `hive_router.py` | `realai/orchestration/hive_router.py` | REVIEW | `_root` | Live has `_product_root` (same role). |
| gold | `orphans/realai/orchestration/hive_router.py` | `hive_router.py` | `realai/orchestration/hive_router.py` | REVIEW | `_root` | Same. |
| backup | `adapters/rackup_coach.py` | `rackup_coach.py` | `modules/organs/meta/rackup_coach.py` | REVIEW | `coach`, `invoke_rackup_coach`, `moderate`, `rackup_coach_status`, `shot_of_the_day` | Live already has `realai/adapters/rackup_coach.py`. |
| backup/gold | `.../organs/base.py` | `base.py` | `realai/plugins/tools/base.py` | REVIEW | `Organ`, `OrganContext`, `OrganResult` | Basename collision; already in `modules/organs/base.py`. |
| gold | `abilities/.../architect_mode.py` | `architect_mode.py` | `abilities/architect_mode.py` | REVIEW | `_compact_repo_view`, `_skip_dir`, `run_architect_mode` | Dupes tree; live authority. |
| gold | `.../code_engineer_cli.py` | `code_engineer_cli.py` | `realai/plugins/tools/code_engineer_cli.py` | REVIEW | `run` | repo_levels twin. |
| gold | `.../nest_orchestrators.py` | `nest_orchestrators.py` | `realai/orchestration/nest_orchestrators.py` | REVIEW | `_inventory`, `_run_nest`, `run`, … | repo_levels twin. |
| gold | `.../registry.py` | `registry.py` | `realai/plugins/registry.py` | REVIEW | `ToolDefinition`, `ToolRegistry` | Different domain (agent_tools_gold). |
| gold | `.../code_engineer_agent.py` | `code_engineer_agent.py` | `abilities/code_engineer_agent.py` | REVIEW | `CodeEngineerAgent` | Twin; leave. |
| gold | `apps/api/main.py` + routes (`audio`,`chat`,`embeddings`,`health`,`models`,`tasks`,`web3`) | *(various)* | schema/plugin same basenames | REVIEW | route handlers | Basename collision API route vs schema — do not merge. |

(~130+ UNIQUE junk rows omitted: openai/pydantic/venv path dumps under backup `plugins/C__*`.)

## Promote decision

**Promoted: none** (0 symbols, 0 files).

No symbol met strict rules (missing from live import AND clear same-package dest). Strongest UNIQUE (`adapters/organs.py`) is already on live outside the gold-root index.

## Smokes

- organs hive_status: organ_count **45**, complete True
- register_plugins: ok (sample_plugin, rackup-coach, atomicfizz*)
- v3_orchestrator --help: ok
- :8001 optional: down (ok)
