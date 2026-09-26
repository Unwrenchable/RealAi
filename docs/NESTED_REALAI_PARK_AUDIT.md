# Nested parks, `recovered/`, and gold-shelf audit (2026-09-26)

Did phase 2–3 parking of the old nested `realai/`, or the in-repo `recovered/` and `imports/` shelves, leave unique product code off live Unwrenchable/RealAi (`live/realai-clean-20260911`)?

**No product implementation needs to come back from what this checkout can read.** 243 of 253 parked Python files under `_quarantine/` are byte-identical to a file already on live. The other 10 do not beat live gold: they are strict subsets, older `realai_core` import paths, a one-line package docstring, SymPy/NumPy debris, or pytest modules whose functions already live under `agent_tools/`, `agents/`, and `realai/plugins/tools/`. In-repo `recovered/` is a placeholder with no Python. `imports/` has four Python files; none beat live gold. This pass copied nothing.

`C:\RealAI-gold` and `D:\RealAI-archive\recovered` are not on this machine. What the repo already records about them is in [External shelves (operator machine)](#external-shelves-operator-machine). This audit does not invent a file list for those paths.

Hive gold stays `realai/orchestration/v3_orchestrator.py`. Bridge gold stays `realai/orchestration/v3_runtime_bridge.py`. `rackup_coach` and `atomicfizz_coach` were not edited. `atomicfizz*` does not appear under `_quarantine/` at all. `rackup_coach.py` on the 2026-09-24 organ shelf is byte-identical to `modules/organs/meta/rackup_coach.py`.

`scanners/promote_gold.py` was not applied. It reads `promote_queue.json` under `REALAI_HOME` and stages into `recovered/`; it does not compare this shelf. The acceptance rule from that tool and from `docs/MONOREPO_MIGRATION_PHASES.md` phase 5 was applied by hand: a parked file comes back only when it beats the live gold file on size **and** unique top-level symbols, and the live file is not an intentional shim.

## Method

- Shelves walked: `_quarantine/twins_20260926/` (primary, phase 2 of 2026-09-26), plus `twins_20260921/`, `twins_20260921_b/`, `twins_20260924/`, `twins_pkg_ui/`, then in-repo `recovered/` and `imports/`.
- Every parked `*.py` (253 quarantine files, 4 under `imports/`, 0 under `recovered/`): sha256 against every live `*.py` outside `_quarantine/`, `imports/`, and `recovered/`, and an AST pass for top-level `def` / `async def` / `class`. Class methods were compared when top-level names matched but the body did not.
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
| **quarantine total** | **253** | **243** | **10** |
| `recovered/` | 0 | 0 | 0 |
| `imports/promoted/` | 4 | 1 | 3 |

Quarantine exceptions are in the tables below. The three non-identical `imports/` files do not beat gold. None were promoted.

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
| `twins_20260921_b/realai__imports/` | IDENTICAL_NOISE | 57 Python files. 56 match a live product file. The organ tree matches `modules/organs/` (`base.py` 1,177 B, `request_path.py` 7,666 B, body/cognitive/dream/evolution/memory/meta/metabolic/nervous). `recovery_plugins/core/local_models.py` (10,692 B) matches only `imports/promoted/local_models.py`, not `realai/core/local_models.py`. Same KEEP_SHELF verdict as that imports file below. Nothing to lift. | — |
| `twins_20260921_b/realai__recovered/` | KEEP_SHELF | No Python. `REALAI_REPO_SCAN.json` and `REALAI_SELF_IMPROVE_CANDIDATES.json` (~1.2 MB scan dumps). | — |
| `twins_20260924/realai__modules__organs/` | IDENTICAL_NOISE | 48/48 Python files byte-identical to `modules/organs/`, including `meta/rackup_coach.py` (2,877 B) and `hive.py` (2,455 B). `request_path.py` matches. Do not recreate `realai/modules/organs` from this shelf. The park note at `realai/modules/organs/README_PARKED.md` can stay. | — |
| `twins_20260924/realai_agents/` | IDENTICAL_NOISE | 43/44 Python files byte-identical to live `agents/` (and a few `realai/` twins such as `realai_hive_orchestrator.py`). `agentx/agents.json` is 234 ids, a subset of live `agents/agentx/agents.json` (258 ids, 224,900 B vs 187,203 B); zero parked ids are missing on live. `access_profiles.json` matches. | — |
| `twins_20260924/realai_agents/hive_orchestrator.py` | KEEP_SHELF | 1,312 B vs live `abilities/hive_orchestrator.py` (1,454 B) and `realai/hive_orchestrator.py` (1,503 B). Same ability id. Parked copy imports only `core.orchestration.hive_router`. Live tries `realai.orchestration.hive_router` first. Zero added symbols. Replacing live would drop the gold import. Hive implementation stays `realai/orchestration/`. | — |
| `twins_20260924/Hey — I'm here..txt` | KEEP_SHELF | 582,398 B chat dump. Not code. | — |
| `twins_pkg_ui/desktop/` | IDENTICAL_NOISE | `__init__.py` (28 B) and `voice_mode.py` (291 B) byte-identical to product-root `desktop/`. | — |

## In-repo `recovered/` and `imports/`

These directories are git placeholders after the 2026-09-13 junction unlink (`docs/recovery/2026-09-13-final-gold/PROMOTE_REPORT.md`). The historical trees were `D:\RealAI-archive\recovered` and `D:\RealAI-archive\imports`. This checkout does not contain those trees.

| parked path | verdict | evidence | live destination if promote |
|-------------|---------|----------|-----------------------------|
| `recovered/` | KEEP_SHELF | `README.txt` only (the same pointer text as `imports/README.txt`: archive on `D:\RealAI-archive\recovered`, gold shelf `C:\RealAI-gold\`). Zero Python. `docs/recovery/realai-import-20260919.md` says a duplicate `realai/realai/` mirror was moved to `recovered/realai-import-20260919/`. That folder is not in this checkout. `docs/unification/GOLD_DEEP_SCAN.md` also names `recovered/from_recycle_bin/` as untracked forensic; it is not here. | — |
| `imports/README.txt` | KEEP_SHELF | Pointer only. Names `D:\RealAI-archive\imports` and `C:\RealAI-gold\`. | — |
| `imports/promoted/__init__.py` | KEEP_SHELF | 846 B. Sole top-level symbol `auto_load_plugins`. Byte-identical to `_quarantine/twins_20260921/realai__plugins__plugins/__init__.py`. Not identical to live `realai/plugins/__init__.py`, which has `list_first_party`, `load_first_party`, `register_all` and the `sys.modules['plugins']` alias. The parked file imports every child of `./plugins` as a side effect of import. Do not overwrite that shim. | — |
| `imports/promoted/local_models.py` | KEEP_SHELF | 10,692 B. Top-level names match live `realai/core/local_models.py` (14,282 B) and `realai/plugins/local_models.py` (13,980 B): `LocalModelType`, `LocalModelManager`, `LocalLLMEngine`, `get_model_manager`, `get_llm_engine`. The imports copy is the smaller AMD/DirectML variant. It has three methods live does not (`LocalModelManager.get_llm`, `LocalLLMEngine._load_peft_transformers`, `LocalLLMEngine._generate_peft_transformers`). Live has the larger loader surface (`list_models`, `register_model`, `is_model_available`, transformers and llama.cpp checks, `unload`). Same top-level symbols, smaller file, less surface. Not a win. The PEFT helpers were not extracted. | — |
| `imports/promoted/self/builder/coding_agent.py` | KEEP_SHELF | 1,277 B. Top-level symbol `CodingAgent` only, same as `realai/coding_agent.py` (1,226 B) and `agents/coding_agent.py` (1,210 B). Body is a different call path (`SelfBuilder.run` plus `workspace_root()`), not a superset of the live `RealAI().chat` agent. Live `realai/coding_agent.py` already uses `REALAI_ROOT` or `C:\RealAI-clean`. Do not replace it with this alternate. | — |
| `imports/promoted/self/builder/test_self_builder.py` | IDENTICAL_NOISE | 1,526 B, class `TestSelfBuilder`. Byte-identical to `tests/test_self_builder.py` and `realai/tests/test_self_builder.py`. | — |

`scripts/recovered/` is scanner JSON (`REALAI_REPO_SCAN.json`, `REALAI_SELF_IMPROVE_CANDIDATES.json`, `GOOD_CODE_ROOTS.json`), not the unlinked archive. It was not treated as a second product tree.

## External shelves (operator machine)

`C:\RealAI-gold` is not mounted here. `D:\RealAI-archive\recovered`, `D:\RealAI-archive\imports`, and `C:\RealAI-clean-backup` are not mounted here. No file under those paths was opened for this pass. The notes below are only what in-repo docs and placeholders already say. They are not a fresh inventory.

Operator follow-up, on the box that has the disks:

1. Inventory `C:\RealAI-gold` (especially `orphans\` and any `.before` orchestrator copies) with the same bar: promote a file only when it beats the live file on size and unique top-level symbols, and the live file is not an intentional shim.
2. Inventory `D:\RealAI-archive\recovered` the same way. Git `recovered/` is the placeholder, not the archive.
3. Do not xcopy either tree onto `live/realai-clean-20260911`.

What the repo already records:

| source | what it says about the external shelf |
|--------|----------------------------------------|
| `recovered/README.txt`, `imports/README.txt`, `_quarantine/README.txt` | Junctions from `C:\RealAI-clean\{recovered,imports,_quarantine}` to `D:\RealAI-archive\...` were unlinked on purpose. D: data was not deleted. Gold shelf path named: `C:\RealAI-gold\`. |
| `docs/AUTHORITY.md` | Gold shelf is `C:\RealAI-gold`. Quarantine data is `D:\RealAI-archive\_quarantine`. |
| `docs/recovery/2026-09-13-final-gold/PROMOTE_REPORT.md` | 2026-09-13 copy from the gold shelf onto live only where the live path was missing or empty: **1,760 files**, 505,474,950 bytes, 0 missing-gold, 21 skipped because live was non-empty. Then the three junctions were removed. After unlink, D: still existed: `recovered` top_entries=45 (sample 501 files / 120,142,517 bytes), `imports` top_entries=1 (sample 399 files / 2,720,044 bytes), `_quarantine` top_entries=347 (sample 507 files / 262,666,148 bytes). Those sample counts are from that log, not a listing this pass could re-read. |
| `docs/recovery/2026-09-13-final-gold/MANIFEST.md` | Static unique-hash pass of D: archives vs live, then copy onto the gold shelf: **5,249 files**, 570,731,925 bytes, of which **3,489** orphan `.py` under `orphans/`. Unique candidate hashes 6,623. Rule in the manifest: copy `C:\RealAI-gold\<rel>` to live only if the dest is still empty; orphans need manual placement; do not wholesale-promote nested Recovery or grok_export trees. The manifest's "top interesting" rows are archive paths from that day (organ `hive.py` / `base.py`, `self_builder.py`, desktop_unique examples, torch QAT stubs). Several of those basenames now live at `modules/organs/` and `realai/core/` in this checkout; this pass did not re-stat the D: originals. |
| `docs/SHELF_CONTENT_DELTA.md` (2026-09-21) | Operator-machine scan, cap 400 `.py` per shelf. Gold top-level `~py` counts recorded then: abilities 14, agents 12, apps 11, frontend 0, orphans 3,488, packages 2, providers 2, realai 292, scripts 16. Raw scan: IDENTICAL 218, NOISE 154, REVIEW 19, UNIQUE 136, PROMOTED 0. After junk filter, ~6 clean UNIQUE and 19 clean REVIEW. Clean gold rows called out and left parked: `orphans/` `cli-hive-commands-world.py`, `agent_activity.before.py`, `v3_orchestrator.before-*.py`, `configuration_bridgetower.py` (HF config). `hive_router.py` REVIEW was `_root` vs live `_product_root`. `base.py` REVIEW was a basename collision; `Organ` already in `modules/organs/base.py`. Backup shelf `C:\RealAI-clean-backup` was scanned in the same doc (recovered ~96 `.py` on that backup, not in this git tree) and also promoted nothing. |
| `docs/recovery/2026-09-19-gold-unique-promote.json` | Later gold-shelf copy into live scripts only: `scripts/promote_eval.py` (797 B) and `scripts/ability_matrix.py` (1,467 B). Note in the file: gold `scripts/`, `packages/`, and `providers/` were already on live; orphans and `C__` dumps skipped. |
| `docs/recovery/realai-import-20260919.md` | Claims `recovered/realai-import-20260919/` holds the old nested `realai/realai/` mirror, and that the overlapping files were older or smaller than live `api_server.py`, `tools.py`, `v3_orchestrator.py`, `server/app.py`, `server/tools_runtime.py`. The folder is absent here. |
| `docs/unification/GOLD_DEEP_SCAN.md` | Names local-only dirt still outside git at the time of that note: `recovered/from_recycle_bin/`, `realai_og_mess/`, `_hold_untracked_*`, `C:\realai_giant_hold\`. Not readable from this checkout. |
| `docs/MONOREPO_TARGET_LAYOUT.md`, `docs/MONOREPO_MIGRATION_PHASES.md` | Shelves stay libraries. Prior deltas recorded zero promotions. Phase 5 still requires size and unique symbols, and forbids merging `C:\RealAI-gold`, `C:\RealAI-clean-backup`, `D:\RealAI-archive`, `recovered/`, or `imports/` onto live. |

## What should come back

Nothing from the trees this checkout can read.

- Orchestration, plugins, organs, abilities, bot, and core gold are not missing a parked sibling that is both larger and symbol-richer.
- Coach files on the quarantine shelf match live. They stay where they are.
- The three `realai-core` pytest modules are the only optional follow-up from `_quarantine/`, and only as new tests with imports rewritten to the live modules named above. They do not replace any gold file.
- Do not revive the `QUARANTINE_DELTA.md` basename candidates. They are aliases.
- Do not promote `imports/promoted/local_models.py` or `coding_agent.py` over the live modules. The PEFT helpers and the `SelfBuilder` coding agent are alternate bodies, not larger gold.
- `C:\RealAI-gold` and `D:\RealAI-archive\recovered` still need an operator-machine pass. The 2026-09-21 shelf delta already promoted zero files from the gold shelf and told the operator to leave `orphans/` and `.before` copies parked.

## Not done

No file was copied. No shim was overwritten. `npm` / pytest / `:8001` were not run; this pass did not change runtime code.
