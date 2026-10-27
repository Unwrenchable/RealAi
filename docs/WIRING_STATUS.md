# Wiring status (2026-10-16)

Generated from a static import graph of the `feat/hive-wire-audit` tree (canonical, non-test, non-duplicate `.py` only;
duplicates resolved by `config/canonical_paths.json`). Machine-readable: `config/wiring_status.json`.
Nothing was moved or parked in this pass; move candidates would go to `D:\ARCHIVE` after approval.

## Counts

| class | before | after | meaning |
|---|---:|---:|---|
| wired | 428 | 440 | statically reachable from an entry point, the ability catalog, or hive_tools/self_data |
| wired_dynamic | 52 | 52 | loaded by name at runtime (organs loader create_organ; .github/agents script_path) |
| wired_via_tool | 1 | 1 | state exposed read-only through a hive tool; module itself not run |
| shim | 41 | 41 | compat re-export of a canonical module; nothing to wire |
| helper | 46 | 37 | imported only by unwired code; follows its parent |
| wire | 4 | 2 | intended feature, not wired yet (next batch) |
| dry_run | 10 | 10 | side-effecting feature; wire only as dry-run/report (not done here) |
| standalone | 262 | 262 | hand-run CLI / maintenance / example script; not a product surface |
| superseded | 63 | 63 | older twin/variant of a canonical module |
| dead | 100 | 100 | vendored third-party, placeholder, learned stub, or non-Python |
| decision | 80 | 80 | needs Travis's decision |
| **total** | 1087 | 1088 | |

Before = c994cc3 with the same classifier (the old 2026-10-12 audit counted 218 wired / 257 orphaned unique files with a coarser
graph that did not see dynamic organ/agent loading). Newly wired this pass: 12 files (below).

## New hive tools (read-only / dry-run, `realai/hive_tools/wired.py`)

| batch | tool | wraps | safety |
|---|---|---|---|
| memory | memory_stats | hive memory.sqlite3 (snapshot copy, read-only URI) | no writes |
| multi-agent | agent_pipeline_plan | agents.agent_runtime.MultiAgentPipeline + realai.core_hive_router.route_model | plan only, no model call |
| multi-agent | hive_routes_status | realai.core_hive_router.register_routes | read-only |
| money (read-only) | payout_check | rackup_coach.money_audit.payout_sanity | never authorizes/sends payouts |
| tools registry | tool_registry_lookup | realai.tools.ToolRegistry + hive_tools merge | read-only |
| dry-run reports | self_heal_status | realai.self_heal.status | report only, no heal/promote |
| dry-run reports | executive_goals | realai.executive goals.jsonl snapshot + watcher names | no tick/act, no mkdir |

Live gating: `realai.tools.TOOL_REGISTRY` merges hive_tools and the opt-in live tool loop (`REALAI_TOOL_LOOP`) offers the
wire-audit tools only when `REALAI_HIVE_TOOLS=1`. Default off, so live behaviour is unchanged. self_data/spotcheck always see them.

## Newly wired files

- `abilities/secure_tools.py`
- `agents/agent_runtime.py`
- `realai/core/tools/hive_executor.py`
- `realai/core_hive_router.py`
- `realai/executive/evidence.py`
- `realai/executive/goal.py`
- `realai/executive/loop.py`
- `realai/executive/watchers/__init__.py`
- `realai/executive/watchers/caps_watch.py`
- `realai/executive/watchers/rackup_health.py`
- `realai/executive/watchers/repo_health.py`
- `realai/hive_tools/wired.py`

## Remaining intended (wire / dry_run)

- [dry_run] `abilities/auto_wire.py` (145 lines): side-effecting (writes/pushes/applies); intended feature, expose only as dry-run/report
- [dry_run] `abilities/delta_extractor.py` (120 lines): side-effecting (writes/pushes/applies); intended feature, expose only as dry-run/report
- [dry_run] `abilities/notifier.py` (57 lines): side-effecting (writes/pushes/applies); intended feature, expose only as dry-run/report
- [dry_run] `abilities/orchestration_worker.py` (57 lines): side-effecting (writes/pushes/applies); intended feature, expose only as dry-run/report
- [dry_run] `realai/core/agents/self_heal.py` (400 lines): side-effecting (writes/pushes/applies); intended feature, expose only as dry-run/report
- [dry_run] `realai/plugins/self_improvement.py` (407 lines): side-effecting (writes/pushes/applies); intended feature, expose only as dry-run/report
- [dry_run] `realai/plugins/tools/self_extend_tool.py` (56 lines): side-effecting (writes/pushes/applies); intended feature, expose only as dry-run/report
- [dry_run] `realai/plugins/tools/self_repair_tool.py` (75 lines): side-effecting (writes/pushes/applies); intended feature, expose only as dry-run/report
- [dry_run] `realai/plugins/tools/tools/harden_repos.py` (938 lines): side-effecting (writes/pushes/applies); intended feature, expose only as dry-run/report
- [dry_run] `realai/plugins/tools/tools/rollout_all_repos.py` (878 lines): side-effecting (writes/pushes/applies); intended feature, expose only as dry-run/report
- [wire] `agents/agent_protocol.py` (208 lines): ReAct parser/prompt for weak local models (deterministic) — next batch: tool loop fallback parser
- [wire] `agents/executor.py` (44 lines): TaskExecutor over planner/worker/critic/synth — next batch: dry-run plan (agent_pipeline_plan covers the pipeline view)

## Needs Travis's decision

| path | lines | question |
|---|---:|---|
| `.github/agents/coder.json.py` | 0 | orphan with no clear owner; wire or retire? |
| `abilities/approval_ui.py` | 49 | UI surface (Flask/web dashboard) — not a training target; wire or retire? |
| `abilities/effective_engine_main_leads.py` | 35 | orphan with no clear owner; wire or retire? |
| `agent_tools/amd_inference.py` | 65 | orphan with no clear owner; wire or retire? |
| `agent_tools/crypto.py` | 31 | orphan with no clear owner; wire or retire? |
| `agent_tools/dashboard.py` | 1115 | UI surface (Flask/web dashboard) — not a training target; wire or retire? |
| `agent_tools/filesystem.py` | 63 | orphan with no clear owner; wire or retire? |
| `agent_tools/http.py` | 27 | orphan with no clear owner; wire or retire? |
| `agent_tools/loader.py` | 146 | orphan with no clear owner; wire or retire? |
| `agent_tools/logger.py` | 43 | orphan with no clear owner; wire or retire? |
| `agent_tools/router.py` | 72 | orphan with no clear owner; wire or retire? |
| `agent_tools/runtime.py` | 305 | UI surface (Flask/web dashboard) — not a training target; wire or retire? |
| `agent_tools/solana.py` | 27 | orphan with no clear owner; wire or retire? |
| `agent_tools/tts_engine.py` | 157 | orphan with no clear owner; wire or retire? |
| `agent_tools/voice__init__.py` | 17 | orphan with no clear owner; wire or retire? |
| `agents/base.py` | 16 | orphan with no clear owner; wire or retire? |
| `agents/coding_agent.py` | 41 | orphan with no clear owner; wire or retire? |
| `agents/critic.py` | 25 | orphan with no clear owner; wire or retire? |
| `agents/hierarchical/__init__.py` | 50 | orphan with no clear owner; wire or retire? |
| `agents/hierarchical/tools.py` | 131 | orphan with no clear owner; wire or retire? |
| `agents/orchestration/__init__.py` | 13 | orphan with no clear owner; wire or retire? |
| `agents/planner.py` | 41 | orphan with no clear owner; wire or retire? |
| `agents/queues.py` | 20 | orphan with no clear owner; wire or retire? |
| `agents/self_training_agent.py` | 19 | orphan with no clear owner; wire or retire? |
| `agents/synthesizer.py` | 25 | orphan with no clear owner; wire or retire? |
| `agents/types.py` | 16 | orphan with no clear owner; wire or retire? |
| `agents/worker.py` | 78 | orphan with no clear owner; wire or retire? |
| `billing/__init__.py` | 93 | orphan with no clear owner; wire or retire? |
| `desktop/voice_mode.py` | 15 | orphan with no clear owner; wire or retire? |
| `modules/desktop_unique/standalone_ai.py` | 6 | orphan with no clear owner; wire or retire? |
| `modules/orchestrators/orchestrator_orchestration.py` | 69 | orphan with no clear owner; wire or retire? |
| `modules/orchestrators/orchestrator_router.py` | 322 | orphan with no clear owner; wire or retire? |
| `packages/sdk-py/realai/__init__.py` | 54 | orphan with no clear owner; wire or retire? |
| `providers/local_llama.py` | 29 | orphan with no clear owner; wire or retire? |
| `realai/agent_tools_gold/__init__.py` | 31 | orphan with no clear owner; wire or retire? |
| `realai/app_framework.py` | 376 | app framework (376 lines), imported once; unclear product role |
| `realai/aura_pkg/memory/engine.py` | 81 | orphan with no clear owner; wire or retire? |
| `realai/billing/__init__.py` | 93 | orphan with no clear owner; wire or retire? |
| `realai/cli-hive-banner.py` | 162 | orphan with no clear owner; wire or retire? |
| `realai/core/memory/json_engine.py` | 29 | orphan with no clear owner; wire or retire? |
| `realai/core/voice/asr_base.py` | 11 | orphan with no clear owner; wire or retire? |
| `realai/core/voice/tts_base.py` | 11 | orphan with no clear owner; wire or retire? |
| `realai/craft.py` | 3233 | realai-craft streaming agent (3,233 lines); console script points at realai/cli/craft.py — which is canonical? |
| `realai/executive/__init__.py` | 10 | orphan with no clear owner; wire or retire? |
| `realai/inference/agent.py` | 100 | orphan with no clear owner; wire or retire? |
| `realai/learn/__init__.py` | 34 | orphan with no clear owner; wire or retire? |
| `realai/memory/hive/memory.py` | 9 | orphan with no clear owner; wire or retire? |
| `realai/memory/memory/__init__.py` | 25 | orphan with no clear owner; wire or retire? |
| `realai/memory/memory/long_term_engine.py` | 3 | orphan with no clear owner; wire or retire? |
| `realai/memory/realai2_server/memory_store.py` | 90 | orphan with no clear owner; wire or retire? |
| `realai/memory/reasoning/core.py` | 81 | AURA ReasoningEngine calls a local LLM over HTTP (non-deterministic) — keep as planner backend or retire? not groundable for self_data |
| `realai/memory/recycle_py/realai-ish_memory_summarizer_agent.py` | 185 | orphan with no clear owner; wire or retire? |
| `realai/memory/sqlite_memory.py` | 141 | per-user profile/interaction store (PII; init_db writes) — wire as a live memory backend, or retire? not training-safe |
| `realai/memory/tools/memory_inspector_ui.py` | 291 | UI surface (Flask/web dashboard) — not a training target; wire or retire? |
| `realai/models/__init__.py` | 22 | orphan with no clear owner; wire or retire? |
| `realai/models/candidate.py` | 30 | orphan with no clear owner; wire or retire? |
| `realai/orchestrators/realai-ish_test_orchestration.py` | 63 | orphan with no clear owner; wire or retire? |
| `realai/plugins/plugin_memory.py` | 70 | orphan with no clear owner; wire or retire? |
| `realai/plugins/plugin_sample_plugin.py` | 34 | orphan with no clear owner; wire or retire? |
| `realai/plugins/tools/_shared.py` | 25 | orphan with no clear owner; wire or retire? |
| `realai/plugins/tools/from_aura_p0_hunt/device_selector.py` | 46 | orphan with no clear owner; wire or retire? |
| `realai/plugins/tools/system_scan_tool.py` | 127 | orphan with no clear owner; wire or retire? |
| `realai/providers/adapter_router.py` | 20 | orphan with no clear owner; wire or retire? |
| `realai/providers/llama_cpp_gpu.py` | 35 | orphan with no clear owner; wire or retire? |
| `realai/providers/realai_embeddings.py` | 36 | orphan with no clear owner; wire or retire? |
| `realai/providers/voice.py` | 42 | orphan with no clear owner; wire or retire? |
| `realai/realai_hive_orchestrator.py` | 292 | second hive orchestrator (292 lines) overlapping realai/orchestration; keep or retire? |
| `realai/runtime/config.py` | 167 | orphan with no clear owner; wire or retire? |
| `realai/scripts/scan_and_reconstruct.py` | 150 | PowerShell saved as .py (unparsable) — rename to .ps1 or retire? (not moved) |
| `realai/sdk-py/__init__.py` | 54 | orphan with no clear owner; wire or retire? |
| `realai/server/native_bootstrap.py` | 48 | orphan with no clear owner; wire or retire? |
| `realai/tools/architect_mode.py` | 47 | orphan with no clear owner; wire or retire? |
| `realai/tools/visualizer.py` | 420 | orphan with no clear owner; wire or retire? |
| `realai/ui/realai_gui.py` | 648 | UI surface (Flask/web dashboard) — not a training target; wire or retire? |
| `realai/utilities/availability.py` | 77 | orphan with no clear owner; wire or retire? |
| `realai/utilities/dimacs.py` | 69 | orphan with no clear owner; wire or retire? |
| `realai/voice/__init__.py` | 34 | orphan with no clear owner; wire or retire? |
| `realai/voice/__main__.py` | 5 | orphan with no clear owner; wire or retire? |
| `realai/voice/asr_base.py` | 11 | orphan with no clear owner; wire or retire? |
| `sdk/python/realai_client.py` | 103 | orphan with no clear owner; wire or retire? |

## superseded (63)

<details><summary>list</summary>

- `abilities/ability_catalog.py`: older ability catalog; canonical is realai/ability_catalog.py (wired)
- `abilities/rackup/__init__.py`: older flat copy of realai/plugins/rackup_coach module (canonical per ONE_TREE)
- `modules/orchestrators/orchestrator_agent_runtime.py`: twin of agents/agent_runtime.py (product-root agents/ wins)
- `modules/orchestrators/realai__v3_orchestrator.py`: twin of hive gold realai/orchestration/v3_orchestrator.py
- `realai/_legacy_main.py`: old server/lambda/vercel entrypoint; superseded by realai/server + realai/orchestration/v3_orchestrator (AUTHORITY.md)
- `realai/agent_runtime/agent_runtime/__init__.py`: nested twin package of agents/agent_runtime.py
- `realai/agent_runtime/realai/agent_runtime.py`: nested twin of agents/agent_runtime.py
- `realai/api/errors.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/api/health.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/api/index.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/api/main.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/core/api/errors.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/core/api/schemas/audio.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/core/api/schemas/chat.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/core/api/schemas/embeddings.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/core/api/schemas/models.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/core/api/schemas/tasks.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/core/api/schemas/web3.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/core/api_server.py`: old server/lambda/vercel entrypoint; superseded by realai/server + realai/orchestration/v3_orchestrator (AUTHORITY.md)
- `realai/core/inference/llamacpp_backend.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/core/inference/vllm_backend.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/core/models/base.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/core/models/registry.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/core/models/stub.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/inference/vllm_backend.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/middleware/authentication.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/middleware/logging.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/orchestrators/nested_realai_v3_orchestrator.py`: nested twin of hive gold realai/orchestration/v3_orchestrator.py (AUTHORITY.md)
- `realai/plugins/api_big_server.py`: old server/lambda/vercel entrypoint; superseded by realai/server + realai/orchestration/v3_orchestrator (AUTHORITY.md)
- `realai/plugins/benchmarks/bench_tool_use.py`: old server/lambda/vercel entrypoint; superseded by realai/server + realai/orchestration/v3_orchestrator (AUTHORITY.md)
- `realai/plugins/client.py`: old server/lambda/vercel entrypoint; superseded by realai/server + realai/orchestration/v3_orchestrator (AUTHORITY.md)
- `realai/plugins/coach_agent.py`: older flat copy of realai/plugins/rackup_coach module (canonical per ONE_TREE)
- `realai/plugins/lambda_chat.py`: old server/lambda/vercel entrypoint; superseded by realai/server + realai/orchestration/v3_orchestrator (AUTHORITY.md)
- `realai/plugins/lambda_core.py`: old server/lambda/vercel entrypoint; superseded by realai/server + realai/orchestration/v3_orchestrator (AUTHORITY.md)
- `realai/plugins/lambda_core_shared.py`: old server/lambda/vercel entrypoint; superseded by realai/server + realai/orchestration/v3_orchestrator (AUTHORITY.md)
- `realai/plugins/lambda_embeddings_audio.py`: old server/lambda/vercel entrypoint; superseded by realai/server + realai/orchestration/v3_orchestrator (AUTHORITY.md)
- `realai/plugins/lambda_image.py`: old server/lambda/vercel entrypoint; superseded by realai/server + realai/orchestration/v3_orchestrator (AUTHORITY.md)
- `realai/plugins/lambda_video.py`: old server/lambda/vercel entrypoint; superseded by realai/server + realai/orchestration/v3_orchestrator (AUTHORITY.md)
- `realai/plugins/organs_bridge.py`: older flat copy of realai/plugins/rackup_coach module (canonical per ONE_TREE)
- `realai/plugins/rating_update.py`: older flat copy of realai/plugins/rackup_coach module (canonical per ONE_TREE)
- `realai/plugins/realai_gui.py`: old server/lambda/vercel entrypoint; superseded by realai/server + realai/orchestration/v3_orchestrator (AUTHORITY.md)
- `realai/plugins/registry.py`: stale twin of agent_tools/registry.py (gold, wired); imports missing .models
- `realai/plugins/related/ability_catalog.py`: older ability catalog; canonical is realai/ability_catalog.py (wired)
- `realai/plugins/shot_of_the_day.py`: older flat copy of realai/plugins/rackup_coach module (canonical per ONE_TREE)
- `realai/plugins/train_directml.py`: old training script; superseded by realai/training (train_sft, dataset_builder)
- `realai/plugins/train_from_agent_manifests.py`: old training script; superseded by realai/training (train_sft, dataset_builder)
- `realai/plugins/train_qwen_lora_directml.py`: old training script; superseded by realai/training (train_sft, dataset_builder)
- `realai/routes/__init__.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/routes/audio.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/routes/chat.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/routes/embeddings.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/routes/health.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/routes/metrics.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/routes/models.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/routes/tasks.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/routes/voice_ws.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/routes/web3.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/schemas/audio.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/schemas/embeddings.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/schemas/models.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/schemas/web3.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/server/api.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)
- `realai/server/vercel_main.py`: week-1/2 FastAPI provider app; live API is realai/server + v3_orchestrator (AUTHORITY.md)

</details>

## dead (100)

<details><summary>list</summary>

- `agents/router.py`: placeholder: source missing
- `apps/vscode/py/pydevd_extension_api.py`: vendored third-party code (pygments/mypy/pydevd/hypothesis/pydantic/pytest/setuptools)
- `packages/weakref_finalize.py`: vendored third-party library copy (huggingface_hub/torch/transformers/gradio/fastapi utils)
- `realai/agent_tools_gold/engine/memory.py`: placeholder: source missing
- `realai/api/autograd.py`: vendored third-party library copy (huggingface_hub/torch/transformers/gradio/fastapi utils)
- `realai/api/remote_module.py`: vendored third-party library copy (huggingface_hub/torch/transformers/gradio/fastapi utils)
- `realai/api/signatures.py`: vendored third-party library copy (huggingface_hub/torch/transformers/gradio/fastapi utils)
- `realai/config/error_reporting.py`: vendored third-party library copy (huggingface_hub/torch/transformers/gradio/fastapi utils)
- `realai/config/expand.py`: vendored third-party library copy (huggingface_hub/torch/transformers/gradio/fastapi utils)
- `realai/context/__init__.py`: vendored third-party library copy (huggingface_hub/torch/transformers/gradio/fastapi utils)
- `realai/datasets/glue.py`: vendored third-party library copy (huggingface_hub/torch/transformers/gradio/fastapi utils)
- `realai/engine/executor.py`: placeholder: source missing
- `realai/engine/loader.py`: placeholder: source missing
- `realai/engine/logger.py`: placeholder: source missing
- `realai/examples/setup.py`: vendored third-party code (pygments/mypy/pydevd/hypothesis/pydantic/pytest/setuptools)
- `realai/inference/_async_client.py`: vendored third-party library copy (huggingface_hub/torch/transformers/gradio/fastapi utils)
- `realai/inference/_client.py`: vendored third-party library copy (huggingface_hub/torch/transformers/gradio/fastapi utils)
- `realai/inference/audio_classification.py`: vendored third-party library copy (huggingface_hub/torch/transformers/gradio/fastapi utils)
- `realai/inference/baseten.py`: vendored third-party library copy (huggingface_hub/torch/transformers/gradio/fastapi utils)
- `realai/metrics/api.py`: vendored third-party library copy (huggingface_hub/torch/transformers/gradio/fastapi utils)
- `realai/metrics/squad_metrics.py`: vendored third-party library copy (huggingface_hub/torch/transformers/gradio/fastapi utils)
- `realai/middleware/asyncexitstack.py`: vendored third-party library copy (huggingface_hub/torch/transformers/gradio/fastapi utils)
- `realai/plugins/_hypothesis_plugin.py`: vendored third-party code (pygments/mypy/pydevd/hypothesis/pydantic/pytest/setuptools)
- `realai/plugins/_schema_validator.py`: vendored third-party code (pygments/mypy/pydevd/hypothesis/pydantic/pytest/setuptools)
- `realai/plugins/effective_engine_main_coach/__init__.py`: learned stub (git-learn), no runtime
- `realai/plugins/effective_engine_main_coach/abilities/__init__.py`: learned stub (git-learn), no runtime
- `realai/plugins/effective_engine_main_coach/abilities/agents_bridge.py`: learned stub (git-learn), no runtime
- `realai/plugins/effective_engine_main_coach/abilities/fastify_context.py`: learned stub (git-learn), no runtime
- `realai/plugins/effective_engine_main_coach/abilities/health.py`: learned stub (git-learn), no runtime
- `realai/plugins/effective_engine_main_coach/abilities/node_context.py`: learned stub (git-learn), no runtime
- `realai/plugins/effective_engine_main_coach/abilities/repo_map.py`: learned stub (git-learn), no runtime
- `realai/plugins/effective_engine_main_learned/abilities/__init__.py`: learned stub (git-learn), no runtime
- `realai/plugins/effective_engine_main_learned/abilities/agents_bridge.py`: learned stub (git-learn), no runtime
- `realai/plugins/effective_engine_main_learned/abilities/fastify_context.py`: learned stub (git-learn), no runtime
- `realai/plugins/effective_engine_main_learned/abilities/health.py`: learned stub (git-learn), no runtime
- `realai/plugins/effective_engine_main_learned/abilities/node_context.py`: learned stub (git-learn), no runtime
- `realai/plugins/effective_engine_main_learned/abilities/repo_map.py`: learned stub (git-learn), no runtime
- `realai/plugins/mypy_plugin.py`: vendored third-party code (pygments/mypy/pydevd/hypothesis/pydantic/pytest/setuptools)
- `realai/plugins/plugin.py`: vendored third-party code (pygments/mypy/pydevd/hypothesis/pydantic/pytest/setuptools)
- `realai/plugins/plugin___init__.py`: 9,640-line "Grok mega __init__" — ONE_TREE: never promote
- `realai/plugins/plugin_test_realai.py`: vendored third-party code (pygments/mypy/pydevd/hypothesis/pydantic/pytest/setuptools)
- `realai/plugins/py/pydevd_plugin_numpy_types.py`: vendored third-party code (pygments/mypy/pydevd/hypothesis/pydantic/pytest/setuptools)
- `realai/plugins/py/pydevd_plugin_pandas_types.py`: vendored third-party code (pygments/mypy/pydevd/hypothesis/pydantic/pytest/setuptools)
- `realai/plugins/py/pydevd_plugin_utils.py`: vendored third-party code (pygments/mypy/pydevd/hypothesis/pydantic/pytest/setuptools)
- `realai/plugins/pytest_plugin.py`: vendored third-party code (pygments/mypy/pydevd/hypothesis/pydantic/pytest/setuptools)
- `realai/plugins/realai_clean_backup_coach/__init__.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_clean_backup_coach/abilities/__init__.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_clean_backup_coach/abilities/abilities_bridge.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_clean_backup_coach/abilities/adapters_bridge.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_clean_backup_coach/abilities/agents_bridge.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_clean_backup_coach/abilities/docker_context.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_clean_backup_coach/abilities/health.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_clean_backup_coach/abilities/modules_bridge.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_clean_backup_coach/abilities/node_context.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_clean_backup_coach/abilities/packages_bridge.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_clean_backup_coach/abilities/plugins_bridge.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_clean_backup_coach/abilities/pnpm_context.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_clean_backup_coach/abilities/python_context.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_clean_backup_coach/abilities/repo_map.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_clean_backup_coach/abilities/route_v1_audio_speech.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_clean_backup_coach/abilities/route_v1_audio_transcriptions.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_clean_backup_coach/abilities/route_v1_chat_completions.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_clean_backup_coach/abilities/typescript_context.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_gold_coach/__init__.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_gold_coach/abilities/__init__.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_gold_coach/abilities/abilities_bridge.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_gold_coach/abilities/agents_bridge.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_gold_coach/abilities/health.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_gold_coach/abilities/modules_bridge.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_gold_coach/abilities/packages_bridge.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_gold_coach/abilities/plugins_bridge.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_gold_coach/abilities/repo_map.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_gold_coach/abilities/route_healthz.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_gold_coach/abilities/route_readyz.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_gold_coach/abilities/route_v1_audio_speech.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_gold_coach/abilities/route_v1_audio_transcriptions.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_gold_coach/abilities/route_v1_chat_completions.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_gold_coach/abilities/route_v1_embeddings.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_gold_coach/abilities/route_v1_models.py`: learned stub (git-learn), no runtime
- `realai/plugins/realai_gold_coach/abilities/route_v1_models_reload.py`: learned stub (git-learn), no runtime
- `realai/plugins/setup.py`: vendored third-party code (pygments/mypy/pydevd/hypothesis/pydantic/pytest/setuptools)
- `realai/providers/anthropic.py`: placeholder: source missing
- `realai/providers/groq.py`: placeholder: source missing
- `realai/providers/local.py`: placeholder: source missing
- `realai/providers/openai.py`: placeholder: source missing
- `realai/providers/realai.py`: placeholder: source missing
- `realai/providers/router.py`: placeholder: source missing
- `realai/runtime/autotune_cache.py`: vendored third-party library copy (huggingface_hub/torch/transformers/gradio/fastapi utils)
- `realai/scripts/scan_realai.ps1.py`: not Python (PowerShell saved as .py)
- `realai/scripts/scan_realai_roots.ps1.py`: not Python (PowerShell saved as .py)
- `realai/security/api_key.py`: vendored third-party library copy (huggingface_hub/torch/transformers/gradio/fastapi utils)
- `realai/setup.py`: vendored third-party code (pygments/mypy/pydevd/hypothesis/pydantic/pytest/setuptools)
- `realai/templates/remote_module_template.py`: vendored third-party library copy (huggingface_hub/torch/transformers/gradio/fastapi utils)
- `realai/tooling/crypto.py`: placeholder: source missing
- `realai/tooling/filesystem.py`: placeholder: source missing
- `realai/tooling/http.py`: placeholder: source missing
- `realai/tooling/registry.py`: placeholder: source missing
- `realai/tooling/solana.py`: placeholder: source missing
- `realai/utilities/autowrap.py`: vendored sympy autowrap
- `scripts/scan_realai_roots.ps1.py`: not Python (PowerShell saved as .py)

</details>

## standalone (262)

<details><summary>list</summary>

- `abilities/assemble_gold_index.py`: maintenance/CLI script, run by hand (not a product feature)
- `agent_tools/cli.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `agent_tools/overmind_runner.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `apps/api/main.py`: maintenance/CLI script, run by hand (not a product feature)
- `apps/api/routes/audio.py`: maintenance/CLI script, run by hand (not a product feature)
- `apps/api/routes/chat.py`: maintenance/CLI script, run by hand (not a product feature)
- `apps/api/routes/embeddings.py`: maintenance/CLI script, run by hand (not a product feature)
- `apps/api/routes/health.py`: maintenance/CLI script, run by hand (not a product feature)
- `apps/api/routes/models.py`: maintenance/CLI script, run by hand (not a product feature)
- `apps/api/routes/tasks.py`: maintenance/CLI script, run by hand (not a product feature)
- `apps/api/routes/voice_ws.py`: maintenance/CLI script, run by hand (not a product feature)
- `apps/api/routes/web3.py`: maintenance/CLI script, run by hand (not a product feature)
- `apps/vscode/py/typing_extensions.py`: maintenance/CLI script, run by hand (not a product feature)
- `bootstrap.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `docs/recovery/2026-09-13-final-gold/gold_scan.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `docs/recovery/2026-09-13-final-gold/promote_and_unlink.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `docs/recovery/_probe_backup_queue.py`: maintenance/CLI script, run by hand (not a product feature)
- `docs/recovery/_probe_live_exec.py`: maintenance/CLI script, run by hand (not a product feature)
- `docs/recovery/_run_learn_batch.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `modules/agents_skills/coding_agent.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `modules/desktop_unique/examples.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `modules/desktop_unique/examples_local_ai.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `modules/desktop_unique/examples_ultimate.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `modules/desktop_unique/local_model_cli.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/aura/main.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/aura/reasoning.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/benchmarks/base.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_ability.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_agent.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_agent_eval.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_arit.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_coding.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_discrete_log.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/benchmarks/bench_exp.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_galoispolys.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_integrate.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_limit.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_matrix.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_memory.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_promote.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_reasoning.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_safety.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_solvers.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_special.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_stack.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_stack_health.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_verify.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_world.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/bench_world_model.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/benchmarks/runner.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/core/agents/hierarchical_main.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/core/agents/training_pipeline.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/core/training/eval.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/core/training/finetune.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/examples/assume_constant_result.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/examples/compare.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/examples/examples_limitless.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/examples/local_llama_example.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/mcp/mcp_server.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/memory/assemble_gold_index.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/memory/dds3_deep_gold_map.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/memory/promote_gold.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/memory/recover_archive_gold.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/memory/scan_desktop_missing_gold.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/memory/scan_local_keyword_gold.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/memory/tools/memory_summarizer_cli.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/packages/makefile.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/packages/sdk-py/realai/__init__.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/packages/six.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/plugins/agent-tools-main/sanity_check.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/api_server.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/api_server_backup.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/api_server_cpu.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/build_datasets.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/chat_qwen_lora_directml.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/create_training_runs_json.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/extract_agent_tool_data.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/lambda_advanced.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/main.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/plugin_registry_builder.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/realai_architect_agent.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/realai_full_autonomous.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/realai_local_server.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/realai_rebuilder.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/realai_self_improving_agent.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/self_improving_agent.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/smart_merge_realai.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/tools/approval_ui.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/tools/orchestration_worker.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/tools/retry_rollout_pushes.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/plugins/tools/tools/code_engineer_cli.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/realai_training/unsloth_train.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/repo_hygiene/canonical_paths.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/runtime/loader.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scanners/ingest_realai_roots.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scanners/promote_gold.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/_register_core_agents_promote.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/_register_deep_promote.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/_rewrite_module_wraps.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/_smoke_craft_promote.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/amd_stack_status.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/apply_unification_results.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/auto_update_pipeline.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/bring_back_from.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/catalog_good_code_roots.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/cold_archive_recovered.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/curated_promote.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/dds3_missing_files.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/scripts/deep_promote_scan.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/scripts/deep_promote_wire.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/scripts/deep_unify_walk.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/diff_grok_export.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/diff_imports_promote_allowlist.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/dispatch_training.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/era_map.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/scripts/exportable/realai_server.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/exportable/variants/grok_export_tools.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/scripts/exportable/variants/nested_realai_audit.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/scripts/exportable/variants/nested_realai_recovery_registry.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/exportable/variants/nested_realai_v3_runtime_bridge.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/scripts/find_self_improve_and_lost.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/heal_cli.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/import_external_trees.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/live_gap_agent.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/scripts/monitor_model.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/organize_repo.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/probe_chat.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/scripts/promote_unified_realai.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/quarantine_catalog.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/realai_full_loop_integrator.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/realai_full_loop_integrator_auto.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/realai_full_loop_integrator_auto_final.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/realai_full_loop_integrator_auto_fixed.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/realai_full_loop_integrator_complete.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/realai_full_loop_integrator_final.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/realai_full_loop_integrator_total.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/realai_full_loop_integrator_ultra.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/realai_hive_dashboard.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/scripts/realai_hive_dashboard_pro.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/realai_hive_integrator_v2.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/realai_hive_multi_root_integrator.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/realai_smart_learn_controller.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/register_realai_hive.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/reregister_models.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/scripts/roots_ingest.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/scripts/run_all_repo_scripts.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/scan_repos_for_realai.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/self_improve_loop_smoke.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/setup_local_llama.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/stack_health.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/scripts/train_lora_local.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/train_to_chat_gguf.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/try_load_qwen.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/scripts/unified_structure_validator.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/universal_badass_engine_run.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/verify_matrix.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/scripts/verify_v3_matrix.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/vulkan_chat.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/vulkan_engine.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/vulkan_runtime.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/walk_training_sources.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/wire_hive_agents.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/wire_recovered.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/scripts/wire_training.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/scripts/wire_vulkan_backend.py`: maintenance/CLI script, run by hand (not a product feature)
- `realai/scripts/world_model_merger.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/self_heal_loop.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/tools/detect_models.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/tools/find_all_lora_bits.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/tools/find_lora_files.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/tools/find_lora_in_checkpoint_dir.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/tools/full_training_scanner.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/tools/lora_pipeline.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/tools/realai_architect_autofix.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/tools/realai_architect_summarize.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/tools/realai_build_model_registry.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/tools/realai_lora_training_pipeline.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/tools/realai_run_architect.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/tools/realai_run_architect3.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/tools/realai_run_architect_chunked.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/tools/walk_root.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/training/dataset_builder/__main__.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/training/dataset_builder/fetch_lichess_puzzles.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/training/realai_hive_advanced.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/training/train_sft.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/training/unsloth_train.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai/voice/lab_server.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `realai_training/unsloth_train.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scanners/alt_v4_autonomy_scan.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scanners/backend_scan.py`: maintenance/CLI script, run by hand (not a product feature)
- `scanners/build_puzzle_map.py`: maintenance/CLI script, run by hand (not a product feature)
- `scanners/dds10_merge_plan_validator.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scanners/dds1_dependency_doc_scan.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scanners/dds2_dependency_crosscheck.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scanners/dds4_orphan_modules.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scanners/dds5_unused_features.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scanners/dds6_config_mismatches.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scanners/dds7_doc_code_consistency.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scanners/dds8_runtime_path_integrity.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scanners/dds9_subsystem_completeness_deep.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scanners/fs1_full_spectrum_scan.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scanners/fs2_module_scan.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scanners/lora_scan.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scanners/mcp_scan.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scanners/npc_scan.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scanners/rag_scan.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scanners/scan_model_weights.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scanners/solana_scan.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scanners/stack_health.py`: maintenance/CLI script, run by hand (not a product feature)
- `scanners/tri_v2_worldmodel_scan.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/_brand_agents_ui.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/_extract_agentx_dash.py`: maintenance/CLI script, run by hand (not a product feature)
- `scripts/_merge_agent_tools_agents.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/_restore_quarantine_batch2.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/_restore_quarantine_batch3.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/_restore_quarantine_batch4.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/_smoke_all_abilities_tools_agents.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/_wide_hunt_abilities_agents.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/ability_matrix.py`: maintenance/CLI script, run by hand (not a product feature)
- `scripts/archive_triage.py`: maintenance/CLI script, run by hand (not a product feature)
- `scripts/calibrate_grader.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/catalog_good_code_roots.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/check_training.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/chess_vs_stockfish.py`: maintenance/CLI script, run by hand (not a product feature)
- `scripts/cleanup.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/common.py`: maintenance/CLI script, run by hand (not a product feature)
- `scripts/convert_dataset.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/dds3_missing_files.py`: maintenance/CLI script, run by hand (not a product feature)
- `scripts/deploy_model.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/evaluate_model.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/exportable/orchestrator_overmind_runner.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/exportable/orchestrator_router.py`: maintenance/CLI script, run by hand (not a product feature)
- `scripts/exportable/orchestrator_solana.py`: maintenance/CLI script, run by hand (not a product feature)
- `scripts/find_self_improve_and_lost.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/generate_distillation_data.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/import_agency_agents_into_realai.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/import_vault77_overseer_agents.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/mine_staged_agents.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/monitor_training.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/overmind_runner.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/pkg_content_delta.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/promote_assemble_queue.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/promote_backup_unique.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/promote_eval.py`: maintenance/CLI script, run by hand (not a product feature)
- `scripts/promote_gold.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/promote_gold_unique.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/promote_queue.py`: maintenance/CLI script, run by hand (not a product feature)
- `scripts/register_local_models.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/score_dataset.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/submit_training.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/sync_agency_registry.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/train_lora_local.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/train_to_chat_gguf.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/unified_stack.py`: maintenance/CLI script, run by hand (not a product feature)
- `scripts/validate/data_stats.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/validate/validate_dpo.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/validate/validate_rft.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/validate/validate_sft.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/vulkan_runtime.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `scripts/wire_staged_d_roots.py`: example/demo or hand-run CLI (has __main__, nothing imports it)
- `training/__init__.py`: maintenance/CLI script, run by hand (not a product feature)
- `training/extract_from_agent_tools.py`: example/demo or hand-run CLI (has __main__, nothing imports it)

</details>

## wired_dynamic (52)

<details><summary>list</summary>

- `agents/hive/__init__.py`: hive agent entry via .github/agents/*.json script_path
- `agents/hive/analyst.py`: hive agent entry via .github/agents/*.json script_path
- `agents/hive/architect.py`: hive agent entry via .github/agents/*.json script_path
- `agents/hive/coder.py`: hive agent entry via .github/agents/*.json script_path
- `agents/hive/governor.py`: hive agent entry via .github/agents/*.json script_path
- `agents/hive/memory.py`: hive agent entry via .github/agents/*.json script_path
- `agents/hive/overseer.py`: hive agent entry via .github/agents/*.json script_path
- `agents/hive/router.py`: hive agent entry via .github/agents/*.json script_path
- `modules/organs/body/device_walker_organ.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/body/synthetic_guardian_layer.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/body/synthetic_habitat_awareness.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/body/synthetic_muscular_system.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/body/synthetic_reflex_system.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/body/synthetic_sensory_system.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/body/synthetic_symbiosis_layer.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/cognitive/amygdala.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/cognitive/brainstem.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/cognitive/cerebellum.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/cognitive/corpus_callosum.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/cognitive/frontal_cortex.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/cognitive/hippocampus.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/cognitive/limbic_system.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/cognitive/prefrontal_cortex.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/dream/lucid_dream_mode.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/dream/nightmare_engine.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/dream/synthetic_dream_forge.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/dream/synthetic_shadow_architect.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/evolution/synthetic_dream_reproductive_system.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/evolution/synthetic_evolution_spiral.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/evolution/synthetic_mutation_engine.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/evolution/synthetic_organ_generator.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/memory_ecosystem/architecture_memory.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/memory_ecosystem/dream_memory.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/memory_ecosystem/episodic_memory.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/memory_ecosystem/long_term_memory.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/memory_ecosystem/procedural_memory.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/memory_ecosystem/semantic_memory.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/memory_ecosystem/short_term_memory.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/meta/rackup_coach.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/meta/synthetic_consciousness_layer.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/meta/synthetic_creativity_furnace.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/meta/synthetic_inspiration_cortex.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/meta/synthetic_intuition_layer.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/meta/synthetic_paradox_engine.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/meta/synthetic_soul_layer.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/metabolic/synthetic_circulatory_system.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/metabolic/synthetic_digestive_system.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/metabolic/synthetic_lymphatic_system.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/metabolic/synthetic_respiratory_system.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/nervous/neural_pathway_builder.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/nervous/neuroplasticity_module.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)
- `modules/organs/nervous/synaptic_pruning_engine.py`: organ loaded by modules.organs.hive.load_all_organs (create_organ)

</details>

## shim (41)

<details><summary>list</summary>

- `agents/hierarchical_main.py`: import shim (re-exports canonical; keep, nothing to wire)
- `agents/rise_system.py`: import shim (re-exports canonical; keep, nothing to wire)
- `agents/supervisor.py`: import shim (re-exports canonical; keep, nothing to wire)
- `agents/training_pipeline.py`: import shim (re-exports canonical; keep, nothing to wire)
- `aura/main.py`: import shim (re-exports canonical; keep, nothing to wire)
- `aura/reasoning.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/abilities/__init__.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/agent_tools/__init__.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/core/agents/agent_runtime.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/core/orchestration/v3_orchestrator.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/critique.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/engine.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/engine/router.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/hive_orchestrator.py`: ability wrapper; catalog uses abilities/hive_orchestrator.py
- `realai/nest_orchestrators.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/nested_realai_model_catalog.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/orchestration/nest_orchestrators.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/orchestrators/nest_orchestrators.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/plugins/ability_catalog.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/realai_gui.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/realai_local_server.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/realai_orchestrator.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/realai_self_improving_agent.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/rise_system.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/scripts/ability_inventory.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/scripts/assemble_gold.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/scripts/dds3.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/scripts/gold_index.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/scripts/walk_root.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/self_improving_agent.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/server/logging.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/server/realai_local_server.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/supervisor.py`: import shim (re-exports canonical; keep, nothing to wire)
- `realai/training/directml_vram_safe.py`: import shim (re-exports canonical; keep, nothing to wire)
- `repo_tools/orchestration_worker.py`: import shim (re-exports canonical; keep, nothing to wire)
- `scripts/deep_gold.py`: import shim (re-exports canonical; keep, nothing to wire)
- `scripts/scan_messy_repo.py`: import shim (re-exports canonical; keep, nothing to wire)
- `scripts/training_data.py`: import shim (re-exports canonical; keep, nothing to wire)
- `server/llama_cli_backend.py`: import shim (re-exports canonical; keep, nothing to wire)
- `server/tools_runtime.py`: import shim (re-exports canonical; keep, nothing to wire)
- `tools/__init__.py`: import shim (re-exports canonical; keep, nothing to wire)

</details>

## helper (37)

<details><summary>list</summary>

- `agent_tools/agents_impl/memory_summarizer_agent.py`: imported by unwired code only (wired when its parent is)
- `agent_tools/anthropic.py`: imported by unwired code only (wired when its parent is)
- `agent_tools/engine/__init__.py`: imported by unwired code only (wired when its parent is)
- `agent_tools/engine/executor.py`: imported by unwired code only (wired when its parent is)
- `agent_tools/engine/router.py`: imported by unwired code only (wired when its parent is)
- `agent_tools/executor.py`: imported by unwired code only (wired when its parent is)
- `agent_tools/groq.py`: imported by unwired code only (wired when its parent is)
- `agent_tools/local.py`: imported by unwired code only (wired when its parent is)
- `agent_tools/openai.py`: imported by unwired code only (wired when its parent is)
- `agent_tools/persona.py`: imported by unwired code only (wired when its parent is)
- `agent_tools/realai.py`: imported by unwired code only (wired when its parent is)
- `agents/agents.py`: imported by unwired code only (wired when its parent is)
- `models/__init__.py`: imported by unwired code only (wired when its parent is)
- `realai/agent_runtime/agent_runtime/agent_runtime.py`: imported by unwired code only (wired when its parent is)
- `realai/agent_tools_gold/engine/__init__.py`: imported by unwired code only (wired when its parent is)
- `realai/config/types.py`: imported by unwired code only (wired when its parent is)
- `realai/core/inference/chat_pipeline.py`: imported by unwired code only (wired when its parent is)
- `realai/core/training/directml_vram_safe.py`: imported by unwired code only (wired when its parent is)
- `realai/memory/__init__.py`: imported by unwired code only (wired when its parent is)
- `realai/memory/memory/bridge.py`: imported by unwired code only (wired when its parent is)
- `realai/models/nested_realai_model_catalog.py`: imported by unwired code only (wired when its parent is)
- `realai/orchestrators/__init__.py`: imported by unwired code only (wired when its parent is)
- `realai/plugins/_loader.py`: imported by unwired code only (wired when its parent is)
- `realai/plugins/effective_engine_main_learned/__init__.py`: imported by unwired code only (wired when its parent is)
- `realai/plugins/local_models.py`: imported by unwired code only (wired when its parent is)
- `realai/plugins/tools/tools/base.py`: imported by unwired code only (wired when its parent is)
- `realai/plugins/tools/tools/permissions.py`: imported by unwired code only (wired when its parent is)
- `realai/providers/auto_loader.py`: imported by unwired code only (wired when its parent is)
- `realai/providers/custom_model_provider.py`: imported by unwired code only (wired when its parent is)
- `realai/realai_agent/__init__.py`: imported by unwired code only (wired when its parent is)
- `realai/security/sandbox.py`: imported by unwired code only (wired when its parent is)
- `realai/skills/code.py`: imported by unwired code only (wired when its parent is)
- `realai/skills/core.py`: imported by unwired code only (wired when its parent is)
- `realai/skills/file_io.py`: imported by unwired code only (wired when its parent is)
- `realai/skills/registry.py`: imported by unwired code only (wired when its parent is)
- `realai/skills/web.py`: imported by unwired code only (wired when its parent is)
- `realai/utilities/__init__.py`: imported by unwired code only (wired when its parent is)

</details>
