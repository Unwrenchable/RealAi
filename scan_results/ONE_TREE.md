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
