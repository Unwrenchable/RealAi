# Nested `realai/` park audit (2026-09-26)

Did phase 2–3 parking of the old nested `realai/` leave unique product code off live Unwrenchable/RealAi (`live/realai-clean-20260911`)?

**No. No product implementation needs to come back.** 243 of 253 parked Python files are byte-identical to a file already on live. The other 10 do not beat live gold: they are strict subsets, older `realai_core` import paths, a one-line package docstring, SymPy/NumPy debris, or pytest modules whose functions already live under `agent_tools/`, `agents/`, and `realai/plugins/tools/`. This pass copied nothing.

Hive gold stays `realai/orchestration/v3_orchestrator.py`. Bridge gold stays `realai/orchestration/v3_runtime_bridge.py`. `rackup_coach` and `atomicfizz_coach` were not edited. `atomicfizz*` does not appear under `_quarantine/` at all. `rackup_coach.py` on the 2026-09-24 organ shelf is byte-identical to `modules/organs/meta/rackup_coach.py`.

`scanners/promote_gold.py` was not applied. It reads `promote_queue.json` under `REALAI_HOME` and stages into `recovered/`; it does not compare this shelf. The acceptance rule from that tool and from `docs/MONOREPO_MIGRATION_PHASES.md` phase 5 was applied by hand: a parked file comes back only when it beats the live gold file on size **and** unique top-level symbols, and the live file is not an intentional shim.

## Method

- Shelves walked: `_quarantine/twins_20260926/` (primary, phase 2 of 2026-09-26), plus `twins_20260921/`, `twins_20260921_b/`, `twins_20260924/`, `twins_pkg_ui/`.
- Every parked `*.py` (253 files): sha256 against every live `*.py` outside `_quarantine/`, and an AST pass for top-level `def` / `async def` / `class`.
- Basename hits preferred, in order: `realai/orchestration/`, `realai/plugins/`, `realai/bot/`, `realai/core/`, `abilities/`, `modules/organs/`, `agents/`, then the rest of the tree. A hash match under a different basename still counts as already on live (numbered dump aliases).
- Skipped as product on purpose: README-only trees, `tokenizer.json`, LoRA `adapter_config.json`, VS `DocumentLayout*.json`, SymPy/NumPy modules under `junk_misplaced/`, coach copies, App Builder overlay (that overlay is still at the product root `src/`; it is not in these shelves).

## Counts

| shelf | parked `.py` | byte-identical to some live file | not identical |
|-------|-------------:|---------------------------------:|--------------:|
| `twins_20260926` | 13 | 6 | 7 |
| `twins_20260921` | 89 | 87 | 2 |
| `twins_20260921_b` | 57 | 57 | 0 |
| `twins_20260924` | 92 | 91 | 1 |
| `twins_pkg_ui` | 2 | 2 | 0 |
| **total** | **253** | **243** | **10** |

Non-identical files are listed in [File exceptions](#file-exceptions). None were promoted.

## `twins_20260926` — phase 2 nested dumps

These are the trees `git mv`'d out of `realai/` on 2026-09-26 (`docs/MONOREPO_MIGRATION_PHASES.md`).

| parked path | verdict | evidence | live destination if promote |
|-------------|---------|----------|-----------------------------|
| `twins_20260926/realai__orchestrator-default-run/` | KEEP_SHELF | No Python. `adapter_config.json` (1,056 B) plus `tokenizer.json` (11,422,170 B). Tokenizer dump, not a module. | — |
| `twins_20260926/realai__agent-tools-orchestrator-default-run/` | KEEP_SHELF | `adapter_config.json` only (1,056 B). | — |
| `twins_20260926/realai__agents-orchestrator-default-run/` | KEEP_SHELF | `adapter_config.json` only (1,056 B). | — |
| `twins_20260926/realai__ai-orchestrator-default-run/` | KEEP_SHELF | `adapter_config.json` only (1,056 B). | — |
| `twins_20260926/realai__core_unify_20260830/` | KEEP_SHELF | Two Python files, both under `junk_misplaced/`. `add.py` (43,407 B) is SymPy `Add` / `_addsort` / `_could_extract_minus_sign`. `arrayprint.py` (339 B) is a NumPy `numpy._core.arrayprint` `__getattr__` shim. No RealAI symbols. | — |
| `twins_20260926/realai__exportable/` | IDENTICAL_NOISE | 5/5 Python files byte-identical to live. `orchestrator_orchestration.py` → `realai/orchestrators/orchestrator_orchestration.py`. `orchestrator_overmind_runner.py` → `agent_tools/overmind_runner.py`. `orchestrator_router.py` → `realai/orchestrators/orchestrator_router.py`. `orchestrator_self_improvement.py` → `realai/core/self_improvement.py`. `orchestrator_solana.py` → `agent_tools/solana.py`. | — |
| `twins_20260926/realai__orchestration_gold/` | KEEP_SHELF | README only (3,975 B). Describes `BaseAgent`, `Orchestrator`, `SharedMemory`, `Pipeline`. Those classes already exist (`agents/agent.py`, `modules/orchestrators/memory.py`, `modules/orchestrators/pipeline.py`). No Python to promote. Hive gold is `realai/orchestration/`, not this side folder. | — |
| `twins_20260926/realai__realai-frontend/` | KEEP_SHELF | No Python. Five files, package stub (`package.json` name `realai-frontend`, Next 15.5.15). Live `frontend/package.json` is the same name at Next 15.5.21 and already depends on `@realai/design-system` and `zod`. Parked copy is older, not a fuller app. | — |
| `twins_20260926/realai__v18/` | KEEP_SHELF | `DocumentLayout.json` and `DocumentLayout.backup.json` only. Editor state, not product code. | — |
| `twins_20260926/realai__variants/` | IDENTICAL_NOISE | `realai_clean_orchestrator.py` (6,390 B), class `RealAIOrchestrator`. Byte-identical to `realai/orchestration/legacy_orchestrator.py` (also `realai/orchestrator.py` and `modules/orchestrators/realai__orchestrator.py`). | — |
| `twins_20260926/realai__realai-core/` | KEEP_SHELF | Do not absorb the nest. 2/5 Python files are import-path leftovers of live files (`sanity_check.py`, `tools/rollout_all_repos.py`) with **zero** added top-level symbols. The other three are pytest modules (see below). Non-Python: docs `VERCEL_DEPLOY.md` and `REAL_TIME_EXECUTION.md` match `agent_tools/docs/`; workflow JSON matches `agents/workflows/`. `console/` is a 2.3 KB “Agent Runtime Console” stub, not `apps/vscode` console gold. `schema/agent.schema.json` is an AgentX manifest schema; live `schema/tool.schema.json` is a different contract (`https://realai.ai/schema/tool.schema.json`). `policy.json` is harden-repos input, not a missing organ. | Three test files only, and only after a human rewrites imports. Not copied in this pass. |

### `realai__realai-core` tests — the only promote-shaped files

These are the only parked Python files with top-level symbols that do not already exist on live. They are tests, not implementations. The nested package they import (`realai_core`, and a sibling `tools/harden_repos.py`) is **not** in the shelf. Live `realai/setup.py` still maps `realai_core` → `realai-core/agent_tools`, and live `scripts/sanity_check.py` was already rewritten from `realai_core.*` to `agent_tools.*`. Copying the tests as-is would not import.

| parked file | verdict | unique top-level symbols | why it is not a drop-in | if a human later wants the coverage |
|-------------|---------|--------------------------|-------------------------|-------------------------------------|
| `realai__realai-core/tests/test_registry.py` (2,880 B) | PROMOTE_CANDIDATE | `TestTrainingFocusedAgents` | Imports `realai_core.registry.recommend_profile`. That function is on `agents/registry.py` (4,255 B) and `realai/plugins/registry.py` (same hash). It is **not** on `agent_tools/registry.py`, which has `package_status` instead. The five training agents the test names (`agent-evals-engineer`, `agent-observability-engineer`, `feedback-learning-engineer`, `grounding-engineer`, `ai-incident-responder`) are already in `agents/agentx/agents.json` (258 ids). They are absent from `agent_tools/data/agents.json` (68 ids). | `agents/tests/test_registry.py` or a new test next to `agents/registry.py`, importing `agents.registry`, loading `agents/agentx/agents.json`. Do not point it at `agent_tools.registry`. |
| `realai__realai-core/tests/test_dashboard.py` (9,045 B) | PROMOTE_CANDIDATE | `TestBuildGraphData`, `TestDashboardRoutes`, `TestEventBus`, `_start_test_server`, `dashboard_server` | Imports `realai_core.dashboard` (`DashboardHandler`, `build_graph_data`, `serve`, `_EventBus`). Those symbols already exist on `agent_tools/dashboard.py` (44,268 B), byte-identical to `realai/agent_tools_gold/dashboard.py`. No live `test_dashboard.py`. | `agent_tools/tests/test_dashboard.py` importing `agent_tools.dashboard`. |
| `realai__realai-core/tests/test_hardening.py` (14,817 B) | PROMOTE_CANDIDATE | `TestLoadPolicy`, `TestDetectEcosystems`, `TestBuildSecurityMd`, `TestBuildCodeowners`, `TestDependabotEntry`, `TestBuildDependabotYml`, `TestBuildPrTemplate`, `TestBuildLicenseText`, `TestUpdateReadmeWithLicense`, `TestWriteHardeningFiles` | Inserts `../tools` on `sys.path` and imports `harden_repos`. That module is not in the parked `tools/` folder (only `rollout_all_repos.py` is). Live full module is `realai/plugins/tools/harden_repos.py` (33,106 B) and `realai/core/harden_repos.py` (32,969 B, same hash as `realai/plugins/tools/tools/harden_repos.py`). `abilities/harden_repos.py` is a 1,150 B `run` wrapper, not this API. | A test that imports `realai.plugins.tools.harden_repos` (or `realai.core.harden_repos`). Do not overwrite the abilities wrapper. |

They were **not** copied. They are not high-confidence and not small drop-ins: three files, two different live packages, and an import root the live tree already abandoned. A human can lock one destination per file. Do not merge the `realai-core` nest to make the imports work.

`sanity_check.py` (8,777 B, 10 top-level defs, 0 added vs live) differs from `scripts/sanity_check.py` and `realai/scripts/sanity_check.py` only by `realai_core.*` → `agent_tools.*`. Same line count (250). Promoting it would undo that rewrite.

`tools/rollout_all_repos.py` (42,348 B, 12 top-level defs, 0 added) is the smaller file. Live `realai/plugins/tools/rollout_all_repos.py` (42,692 B) adds the product-root `sys.path` bootstrap and imports `agent_tools.importer`. The parked file imports `realai_core.importer` and sets `ROOT` to `parents[1]`. The same-size twin `realai/plugins/tools/tools/rollout_all_repos.py` differs only in that import line. Not a win.

## Older shelves (already delta'd; re-hashed here)

`docs/QUARANTINE_DELTA.md` and `docs/QUARANTINE_CONTENT_DELTA.md` (2026-09-21) promoted nothing. This pass agrees, and it retires the ten basename-only CANDIDATE rows in `QUARANTINE_DELTA.md`. Nine of them are numbered copies that hash to a live file under a normal name (`realai/plugins/plugin___init__.py`, `realai/plugins/desktop_plugins/__init__.py`, `realai/plugins/plugin_marketplace.py`, `realai/plugins/plugin_sample_plugin.py`, `realai/plugins/plugin_test_realai.py`). The tenth, `plugin_test_realai_8.py`, is a strict subset of that same test module (row below). None of the ten are missing plugins.

| parked path | verdict | evidence | live destination if promote |
|-------------|---------|----------|-----------------------------|
| `twins_20260921/realai__plugins__plugins/` | IDENTICAL_NOISE | 87 Python files. 86 are byte-identical to a live file (`realai/plugins/` gold, including `coach.py` 17,381 B and `coach_agent.py` 5,051 B, or a same-bytes alias). The nine `plugin___init___N.py` / `plugin_*_N.py` names hash to ordinary live files (`plugin___init__.py`, `desktop_plugins/__init__.py`, `plugin_marketplace.py`, `plugin_sample_plugin.py`, `plugin_test_realai.py`). `__init__.py` (846 B, symbol `auto_load_plugins`) matches `imports/promoted/__init__.py`, not live `realai/plugins/__init__.py`. Live authority has `list_first_party`, `load_first_party`, `register_all` and the `sys.modules['plugins']` alias. The parked file auto-imports every child of `./plugins` on import. Do not overwrite that shim. The one non-identical file is the next row. | — |
| `twins_20260921/realai__plugins__plugins/plugin_test_realai_8.py` | IDENTICAL_NOISE | 99,244 B, 135 top-level test functions. Every one of them is already in `realai/plugins/plugin_test_realai.py` (117,601 B). Live has 17 additional tests (`test_model_registry_*`, `test_structured_*`, `test_week*`). Parked file is a strict subset. | — |
| `twins_20260921/realai__plugins__C_realai_plugins/` | KEEP_SHELF | `__init__.py` is 37 bytes: `"""RealAI living plugins package."""`. No defs. Not a second plugin tree. | — |
| `twins_20260921/realai__grok_export_realai/` | IDENTICAL_NOISE | One Python file, `training/build_datasets.py` (1,538 B), byte-identical to `training/build_datasets.py`. Prior content-delta REVIEW symbols (`build_dataset_bundle`) already live there. | — |
| `twins_20260921/realai__deep_nests/` | KEEP_SHELF | No Python. Two ~3.7 MB `nest_*_orchestrators.json` inventories and matching markdown. Not modules. | — |
| `twins_20260921/realai__from_nests/` | KEEP_SHELF | `self_heal_last_cycle.json` only (20,218 B). | — |
| `twins_20260921/realai__realai/` | KEEP_SHELF | Two 2-byte JSON stubs (`plugins/registry.json`, `world_model/world_model.json`). | — |
| `twins_20260921/realai__realai_repo/` | KEEP_SHELF | VS `DocumentLayout*.json` only. | — |
| `twins_20260921/realai__realai_sdk/` | KEEP_SHELF | VS `DocumentLayout*.json` only. | — |
| `twins_20260921/globals.css`, `layout.tsx` | KEEP_SHELF | Root orphan UI parked in phase 2 (1,532 B and 381 B). Not a frontend. Live front door is `frontend/`. | — |
| `twins_20260921_b/realai__imports/` | IDENTICAL_NOISE | 57/57 Python files byte-identical to live. Organ tree matches `modules/organs/` (`base.py` 1,177 B, `request_path.py` 7,666 B, body/cognitive/dream/evolution/memory/meta/metabolic/nervous). `local_models.py` matches `imports/promoted/local_models.py`. Nothing to lift out of `imports/`. | — |
| `twins_20260921_b/realai__recovered/` | KEEP_SHELF | No Python. `REALAI_REPO_SCAN.json` and `REALAI_SELF_IMPROVE_CANDIDATES.json` (~1.2 MB scan dumps). | — |
| `twins_20260924/realai__modules__organs/` | IDENTICAL_NOISE | 48/48 Python files byte-identical to `modules/organs/`, including `meta/rackup_coach.py` (2,877 B) and `hive.py` (2,455 B). `request_path.py` matches. Do not recreate `realai/modules/organs` from this shelf. The park note at `realai/modules/organs/README_PARKED.md` can stay. | — |
| `twins_20260924/realai_agents/` | IDENTICAL_NOISE | 43/44 Python files byte-identical to live `agents/` (and a few `realai/` twins such as `realai_hive_orchestrator.py`). `agentx/agents.json` is 234 ids, a subset of live `agents/agentx/agents.json` (258 ids, 224,900 B vs 187,203 B); zero parked ids are missing on live. `access_profiles.json` matches. | — |
| `twins_20260924/realai_agents/hive_orchestrator.py` | KEEP_SHELF | 1,312 B vs live `abilities/hive_orchestrator.py` (1,454 B) and `realai/hive_orchestrator.py` (1,503 B). Same ability id. Parked copy imports only `core.orchestration.hive_router`. Live tries `realai.orchestration.hive_router` first. Zero added symbols. Replacing live would drop the gold import. Hive implementation stays `realai/orchestration/`. | — |
| `twins_20260924/Hey — I'm here..txt` | KEEP_SHELF | 582,398 B chat dump. Not code. | — |
| `twins_pkg_ui/desktop/` | IDENTICAL_NOISE | `__init__.py` (28 B) and `voice_mode.py` (291 B) byte-identical to product-root `desktop/`. | — |

## What should come back

Nothing in the product tree.

- Orchestration, plugins, organs, abilities, bot, and core gold are not missing a parked sibling that is both larger and symbol-richer.
- Coach files on the shelf match live. They stay where they are.
- The three `realai-core` pytest modules are the only optional follow-up, and only as new tests with imports rewritten to the live modules named above. They do not replace any gold file.
- Do not revive the `QUARANTINE_DELTA.md` basename candidates. They are aliases.

## Not done

No file was copied. No shim was overwritten. `npm` / pytest / `:8001` were not run; this pass did not change runtime code.
