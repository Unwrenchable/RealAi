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
