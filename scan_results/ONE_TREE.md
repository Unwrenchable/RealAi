# One Tree map — 2026-09-24

Frozen from disk + scan_results JSON. No invented winners.

Sources used:
- scan_results/PROMOTED_20260924.json
- scan_results/BUILDER_PROMOTE_HANDOFF.json
- scan_results/HIVE_IMPORT_AUDIT_20260924.json
- scan_results/HIVE_TWIN_SITES_20260924.json
- scan_results/ARCHITECT_MODE_HITS_20260924.json
- git log --oneline -15
- path existence checks on C:\RealAI-clean

## 1. Authority

| Field | Value |
|---|---|
| Root | `C:\RealAI-clean` |
| Branch | `live/realai-clean-20260911` |
| Ahead of origin | 6 |
| promote_gold.py ROOT | `Path(r"C:\RealAI-clean")` at scripts/promote_gold.py:27 |

Do not merge onto live:
- recovery/*
- main
- unification/*

## 2. Winner table

| Package | Winner path | Twin / park path | Shim path | Status |
|---|---|---|---|---|
| abilities | `abilities/` (product-root) | `realai/abilities/` (compat package; DO_NOT_PARK per HIVE_IMPORT_AUDIT) | `realai/abilities/__init__.py` re-exports product-root `abilities` | Live. `architect_mode` body at `abilities/architect_mode.py` (commit 687c55ff; gold from D:\RealAI-archive, sha256 prefix 10c442968eb9f0e0) |
| agents | `agents/` (product-root) | `_quarantine/twins_20260924/realai_agents` | `realai/realai_self_improving_agent.py`, `realai/self_improving_agent.py` → `agents.*` | Twin parked (commit 2b52297a). `realai/agents` gone |
| organs | `modules/organs/` | Body: `_quarantine/twins_20260924/realai__modules__organs`. Marker left at `realai/modules/organs/README_PARKED.md` only | Hive uses `modules.organs` | Body parked. Marker dir remains (not a body) |
| plugins (rackup_coach) | `realai/plugins/rackup_coach` | — | `plugins/rackup_coach/__init__.py` → `realai.plugins.rackup_coach` | Shim live; gold under `realai/plugins/` |
| server | `realai/server/` | — | `server/llama_cli_backend.py`, `server/tools_runtime.py` | Shims from PROMOTED catalog |

Path existence (disk, this freeze):

| Path | Exists |
|---|---|
| `agents/` | yes |
| `realai/agents` | no |
| `_quarantine/twins_20260924/realai_agents` | yes |
| `modules/organs/` | yes |
| `realai/modules/organs` | yes (marker only: README_PARKED.md) |
| `_quarantine/twins_20260924/realai__modules__organs` | yes |
| `abilities/architect_mode.py` | yes |
| `realai/plugins/` | yes |
| `plugins/rackup_coach/` | yes |
| `scripts/promote_gold.py` | yes |

## 3. Promoted 7

From `scan_results/PROMOTED_20260924.json`:

1. `imports/promoted/local_models.py` (if_missing)
2. `imports/promoted/__init__.py` (if_missing)
3. `imports/promoted/self/builder/coding_agent.py` (if_missing)
4. `imports/promoted/self/builder/test_self_builder.py` (if_missing)
5. `server/llama_cli_backend.py` (shim → `realai/server/llama_cli_backend.py`)
6. `server/tools_runtime.py` (shim → `realai/server/tools_runtime.py`)
7. `plugins/rackup_coach/__init__.py` (shim → `realai/plugins/rackup_coach`)

## 4. Hard no

- Grok mega `__init__.py` (do not point at / do not promote wholesale)
- recovery / main / unification merges onto live
- `promote_gold.py` apply
- abilities/ wholesale park
- Full-tree AST walks

## 5. Open

- `realai/craft.py:981` and `realai/cli/craft.py:1066` still `from realai.abilities.architect_mode import run_architect_mode`
- That path works today because `realai/abilities/__init__.py` re-exports product-root `abilities` (load-bearing shim until Slice B)
- Body itself is already at `abilities/architect_mode.py` — craft rewrite is deferred

## 6. Verify last known

Quoted from prior verify-only slice (t10u); not re-run this freeze:

```
IMPORT_OK <function run_architect_mode at 0x0000029D896F96C0>
```

`:8001/health` — `"status":"ok"`, `"service":"realai-v3-orchestrator"`, `"vulkan":{"ok":true,...}`

`:8080/health` — `{"status":"ok"}`

## 7. Cold-start verify freeze (2026-09-24)

- pushed: yes (remote tip `e7af4cc6`)
- cold_start: yes
- chat_non_empty: yes
- verified_at: 2026-09-24 03:54:03 PT

Evidence (fresh this freeze):

- `:8080/health` -> `{"status":"ok"}`
- `:8001/health` -> `"status":"ok"`, `vulkan.ok=true`, service `realai-v3-orchestrator`
- import: `IMPORT_OK <function run_architect_mode ...> True`
- chat `choices[0].message.content` quote: `Hey — RealAI, local on this PC.` (non-empty; model realai-hive)
- abilities count: 65
- tools_count: 117

Path table (re-checked): agents/ yes; realai/agents no; quarantine realai_agents yes; modules/organs/ yes; realai/modules/organs yes (marker); quarantine organs twin yes; abilities/architect_mode.py yes; realai/plugins/ yes; plugins/rackup_coach/ yes; scripts/promote_gold.py yes.

Vulkan start used (canonical `start_realai_server.bat`):
`C:\llama-vulkan\llama-server.exe -m C:\models\checkpoints_lora\qwen2.5-coder-7b-instruct-q5_k_m.gguf --host 127.0.0.1 --port 8080 -c 65536 -ngl 99 --jinja`

Hive: `python -m realai.v3_orchestrator --host 127.0.0.1 --port 8001`

## realai/ top-level dirs

name | class | twin_of | imported | file_count
--- | --- | --- | --- | ---
abilities | shim |  | yes | 11
adapters | unknown |  | no | 15
agent-tools-main | run_dump |  | no | 2
agent-tools-orchestrator-default-run | run_dump |  | no | 1
agent_runtime | nested_tree |  | yes | 55
agent_tools | shim |  | yes | 5
agent_tools_gold | twin_of | agent_tools | yes | 27
agents-orchestrator-default-run | run_dump |  | no | 1
ai-orchestrator-default-run | run_dump |  | no | 1
api | gold_in_realai |  | yes | 20
app | nested_tree |  | yes | 4
apps | nested_tree |  | no | 24701
atomic_fizz | unknown |  | yes | 6
aura | unknown |  | yes | 10
aura_pkg | unknown |  | no | 2
autopilot | unknown |  | no | 2
backend_realai | nested_tree |  | no | 13
benchmarks | unknown |  | yes | 37
billing | unknown |  | no | 1
bin | unknown |  | no | 23
bot | unknown |  | yes | 20
catalog | unknown |  | no | 12
chat | unknown |  | no | 1
cli | gold_in_realai |  | yes | 92
commands | unknown |  | no | 1
components | unknown |  | no | 9
config | unknown |  | yes | 14
context | unknown |  | no | 2
core | gold_in_realai |  | yes | 282
core_unify_20260830 | run_dump |  | no | 2
data | unknown |  | no | 2
datasets | unknown |  | no | 9
docs | unknown |  | no | 31
engine | unknown |  | yes | 11
examples | unknown |  | no | 7
executive | unknown |  | yes | 12
exportable | unknown |  | no | 5
fusion-ui | nested_tree |  | no | 5
inference | unknown |  | no | 12
learn | unknown |  | yes | 30
marketplace | unknown |  | no | 1
mcp | unknown |  | no | 4
memory | gold_in_realai |  | yes | 128
metrics | unknown |  | no | 4
middleware | unknown |  | no | 4
models | unknown |  | yes | 33
modules | gold_in_realai |  | yes | 46
orchestration | gold_in_realai | orchestration_gold | yes | 41
orchestration_gold | twin_of | orchestration | yes | 1
orchestrator | unknown |  | yes | 1
orchestrator-default-run | run_dump |  | no | 2
orchestrators | unknown |  | yes | 15
packages | nested_tree |  | no | 22
plugins | gold_in_realai |  | yes | 436
profiles | unknown |  | no | 1
prompts | unknown |  | no | 7
providers | gold_in_realai |  | yes | 32
python | nested_tree |  | no | 2
realai-backend | nested_tree |  | no | 1
realai-cli | nested_tree |  | no | 1
realai-core | nested_tree |  | no | 24
realai-frontend | nested_tree |  | no | 6
realai-frontend__dup1 | nested_tree |  | no | 1
realai_agent | nested_tree |  | no | 2
realai_training | nested_tree |  | no | 1
registry | unknown |  | no | 2
results | run_dump |  | no | 4
routes | unknown |  | yes | 10
runtime | unknown |  | no | 3
scan_results | run_dump |  | no | 12
scanners | run_dump |  | yes | 5
schema | unknown |  | no | 2
schemas | unknown |  | no | 7
scripts | unknown |  | no | 120
sdk | gold_in_realai |  | yes | 9
sdk-py | nested_tree |  | no | 2
sdk-ts | nested_tree |  | no | 2
security | unknown |  | no | 4
server | gold_in_realai |  | yes | 68
skills | unknown |  | no | 6
static | unknown |  | no | 1
templates | unknown |  | no | 3
tests | unknown |  | yes | 51
tooling | unknown |  | no | 6
tools | unknown |  | yes | 19
tools_realai | unknown |  | no | 1
tracing | unknown |  | no | 2
training | gold_in_realai |  | yes | 30
ui | nested_tree |  | yes | 7
universe | unknown |  | yes | 31
utilities | unknown |  | no | 6
v18 | unknown |  | no | 2
variants | unknown |  | no | 1
voice | nested_tree |  | yes | 32814
web3 | unknown |  | no | 12
widget | nested_tree |  | no | 1
workflows | unknown |  | no | 2
world_model | nested_tree |  | yes | 34
## realai/ unknown import triage

Method: aggregate scoped `rg` over `realai`, `abilities`, `agents`, `modules`, `plugins`, `server`; Python import forms authoritative; required skip globs applied.

### unknown_imported

| name | site_count | sample_files |
|---|---:|---|
| `atomic_fizz` | 4 | `abilities/omnibrain.py`<br>`abilities/overseer.py`<br>`abilities/realai/abilities/overseer.py`<br>`abilities/world_brain.py` |
| `benchmarks` | 1 | `realai/benchmarks/bench_world_model.py` |
| `bot` | 15 | `realai/apps/api/main.py`<br>`realai/apps/api/routes/chat.py`<br>`realai/bot/__init__.py`<br>`realai/bot/easy_tools.py`<br>`realai/bot/live_exec.py` |
| `config` | 1 | `realai/models/loader.py` |
| `executive` | 7 | `realai/executive/__init__.py`<br>`realai/executive/daemon.py`<br>`realai/executive/loop.py`<br>`realai/executive/watchers/__init__.py`<br>`realai/executive/watchers/caps_watch.py` |
| `learn` | 12 | `abilities/learn_git.py`<br>`realai/__main__.py`<br>`realai/cli/craft.py`<br>`realai/cli/hive/commands/learn.py`<br>`realai/learn/__init__.py` |
| `models` | 2 | `realai/model_catalog.py`<br>`realai/nested_realai_model_catalog.py` |
| `routes` | 2 | `realai/api/main.py`<br>`realai/routes/__init__.py` |
| `tests` | 2 | `realai/test_local_server.py`<br>`realai/test_realai.py` |
| `tools` | 25 | `modules/organs/body/synthetic_guardian_layer.py`<br>`realai/api_server.py`<br>`realai/benchmarks/bench_tool_use.py`<br>`realai/core/api_server.py`<br>`realai/core/tools/hive_executor.py` |
| `universe` | 8 | `realai/cli/hive/commands/world.py`<br>`realai/meta_router.py`<br>`realai/universe/__init__.py`<br>`realai/universe/architect.py`<br>`realai/universe/doctor.py` |

### unknown_unused

- `adapters`
- `aura`
- `aura_pkg`
- `autopilot`
- `billing`
- `bin`
- `catalog`
- `chat`
- `commands`
- `components`
- `context`
- `data`
- `datasets`
- `docs`
- `engine`
- `examples`
- `exportable`
- `inference`
- `marketplace`
- `mcp`
- `metrics`
- `middleware`
- `orchestrator`
- `orchestrators`
- `profiles`
- `prompts`
- `registry`
- `runtime`
- `schema`
- `schemas`
- `scripts`
- `security`
- `skills`
- `static`
- `templates`
- `tooling`
- `tools_realai`
- `tracing`
- `utilities`
- `v18`
- `variants`
- `web3`
- `workflows`

### unknown_unscanned

- none

## 8. Tools winner (2026-09-24)

| Path | Exists | Recursive `*.py` count (excluding `__pycache__`) |
|---|---:|---:|
| `tools/` | yes | 1 |
| `realai/tools/` | yes | 19 |
| `realai/core/tools/` | yes | 9 |
| `realai/tools_realai/` | yes | 0 |
| `realai/agent_tools/` | yes | 1 |
| `realai/agent_tools_gold/` | yes | 27 |
| `agent_tools/` (product root) | yes | 60 |

| Decision | Class | Winner |
|---|---|---|
| tools | `gold_in_realai` | `realai/tools` |

Facts: `realai/api_server.py` has two A-form imports from `realai.tools`; `realai/v3_orchestrator.py` is present with no A-D scoped tool import. Scoped AST totals: A=3 hits/2 files, B=4/4, C=0/0, D=4/4. `modules/organs` uses A, not B; no split trigger. `*_gold` is shelf-only.


## 9. Routes winner (2026-09-24)

| Package | Winner path | Class | Evidence |
|---|---|---|---|
| routes | null | `split` | `realai/api_server.py` runs a live stdlib `HTTPServer`/`RealAIAPIHandler` with `do_GET`/`do_POST`; `realai/api/main.py` mounts `realai.routes` on FastAPI |

Disk: product-root `routes/` missing; `realai/routes/` has 10 Python files; `realai/api/` has 14. Scoped imports: A=1 hit/1 file, B=0/0, C=0/0. Two live HTTP routers trigger split. Do not merge `realai/api/` into `realai/routes/`.

## unique scope vs junk

| A gold_runtime path | exists | py_count |
|---|---:|---:|
| abilities | True | 97 |
| agents | True | 45 |
| modules | True | 113 |
| plugins | True | 3 |
| realai/plugins | True | 259 |
| realai/server | True | 26 |
| realai/api | True | 14 |
| realai/cli | True | 30 |
| realai/tools | True | 19 |
| realai/v3_orchestrator.py | True | 1 |
| realai/api_server.py | True | 1 |
| realai/craft.py | True | 1 |
| **A total** |  | **609** |

| B imported_features dir | exists | py_count |
|---|---:|---:|
| realai/atomic_fizz | True | 3 |
| realai/universe | True | 15 |
| realai/learn | True | 11 |
| realai/executive | True | 9 |
| realai/bot | True | 7 |
| realai/routes | True | 10 |
| realai/models | True | 7 |
| realai/config | True | 6 |
| **B total** |  | **68** |

| C catalog item | count | source |
|---|---:|---|
| abilities | 65 | live_8001 |
| tools | 117 | live_8001 |

| D junk-excluded name |
|---|
| .continue |
| .git |
| .learn_cache |
| .pytest_cache |
| .pytest_cache__dup1 |
| .vs |
| __pycache__ |
| _quarantine |
| agent_tools_gold |
| agents-orchestrator-default-run |
| agent-tools-orchestrator-default-run |
| ai-orchestrator-default-run |
| archive |
| core_unify_20260830 |
| logs |
| node_modules |
| orchestration_gold |
| orchestrator-default-run |
| Output |
| realai-frontend__dup1 |

## Capability ledger (2026-09-24)

| class | count |
|---|---:|
| imported_uncatalogued | 80 |
| live | 120 |
| missing_off_gold | 59 |
| orphan_unique | 36 |
| stub_gold | 3 |
| twin | 6 |

orphan_unique:
- __init__.hive_status
- __main__.build_parser
- _legacy_main.build_parser
- _v1_client.AgentExecutionStatus
- ability_catalog.to_wsl_or_native
- agent_activity.with_hive_core
- agent_protocol.build_system_prompt
- api_server.init_db
- app_framework.AppEvent
- cli-hive-banner.render_banner
- cloud_fallback.is_hosted_cloud
- coding_agent.CodingAgent
- core_hive_router.list_nest_orchestrators
- craft.tool_doctor
- hive.tools
- hive_orchestrator.run
- lambda_embeddings_audio.create_embeddings_response
- learn_git.split_learn_rest
- local_media.generate_image_local
- local_runtime.CachedModel
- mcp_server.call_tool
- mcp_vault77.call_tool
- meta_router.RoutingDecision
- model_assets.repo_root
- model_registry.ModelMetadata
- plugin_registry.load_registry
- provider_resolve.default_selfhost_provider
- realai_hive_orchestrator.safe_read
- realai_self_healing_core.safe_read_text
- recovery_registry.resolve_lora_root
- repo_tools.workspace_root
- router.ProviderScore
- self_heal.status
- self_heal_loop.log
- unified_orchestrator.UnifiedOrchestrator
- world_model.Goal

## Orphan buckets (2026-09-24)

- runtime: 14
- readme_gap: 4
- noise: 18
- keep: __init__.hive_status, agent_activity.with_hive_core, api_server.init_db, cloud_fallback.is_hosted_cloud, coding_agent.CodingAgent, craft.tool_doctor, hive.tools, hive_orchestrator.run, lambda_embeddings_audio.create_embeddings_response, local_media.generate_image_local, mcp_server.call_tool, mcp_vault77.call_tool, plugin_registry.load_registry, provider_resolve.default_selfhost_provider, recovery_registry.resolve_lora_root, self_heal.status, self_heal_loop.log, unified_orchestrator.UnifiedOrchestrator, world_model.Goal

## freeze catalog id module map 2026-09-24

| id | modules | kind |
| --- | --- | --- |
| web_research | abilities/web_search.py | stub |
| task_automation | abilities/task_automation.py | stub |
| self_reflection | realai/core/self_improvement.py, realai/core/critique.py | live core |
| training_pipeline | realai/training/training_pipeline.py | live class |
| lora_adapters | realai/recovery_registry.py | list/resolve only |
| frontend_ui | deferred (apps/frontend nested) | WONT this freeze |

- hive catalog file = realai/ability_catalog.py
- health :8001 = ok (PID 6444 python); :8080 = ok (PID 9744 llama-server)
- truth vs freeze: freeze-table module paths all exist on disk as labeled; no path alias note needed this freeze.
