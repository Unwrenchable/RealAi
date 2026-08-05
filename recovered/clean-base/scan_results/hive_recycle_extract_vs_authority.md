# Hive gold diff — Recycle extract vs authority

Generated: `2026-07-15T15:10:55.593290+00:00`

- Extract: `C:\realai\recovered\from_recycle_bin\extracted_realai_core\realai`
- Authority: `C:\realai`
- Extract indexed: **196** | Authority indexed: **15000**
- **Only in extract:** 135
- **Only in authority:** 14939
- Same path, different content: **5**
- Same path, identical: **53**
- Priority only-in-extract: **62**
- Priority content diffs: **0**

## Top-level folders only in extract

- `realai/` — 60 files
- `realai_historical_backups/` — 9 files
- `providers/` — 8 files
- `realai_repo/` — 8 files
- `realai_sdk/` — 8 files
- `tests/` — 8 files
- `realai_memory/` — 7 files
- `src/` — 6 files
- `real-fin/` — 4 files
- `RealAIProject/` — 2 files
- `plugins/` — 2 files
- `realai-clean__dup1/` — 2 files
- `realai-core/` — 2 files
- `realai_good/` — 2 files
- `schema/` — 2 files
- `realai-backend/` — 1 files
- `realai-clean/` — 1 files
- `scripts/` — 1 files
- `training/` — 1 files
- `utilities/` — 1 files

## Priority uniques in extract (first 60)

- `RealAIProject/realai/realai_memory.json`
- `plugins/__init__.py`
- `plugins/sample_plugin.py`
- `providers/registry.ts`
- `real-fin/realai/realai - Copy/realai/realai_memory.json`
- `real-fin/realai/realai - Copy/realai_memory.json`
- `real-fin/realai/realai/realai_memory.json`
- `real-fin/realai/realai_memory.json`
- `realai-core/agent_tools/__init__.py`
- `realai/agent_runtime.py`
- `realai/local_runtime.py`
- `realai/memory/__init__.py`
- `realai/memory/engine.py`
- `realai/model_registry.py`
- `realai/models/realai-embed/README.md`
- `realai/models/realai-overseer/README.md`
- `realai/models/registry.json`
- `realai/plugin_marketplace.py`
- `realai/realai - Copy/realai/realai_memory.json`
- `realai/realai - Copy/realai_memory.json`
- `realai/realai/realai_memory.json`
- `realai/realai_memory.json`
- `realai/router.py`
- `realai/self_improvement.py`
- `realai/server/embeddings.py`
- `realai/server/embeddings_backend.py`
- `realai/server/memory_store.py`
- `realai/server/orchestration.py`
- `realai/server/router.py`
- `realai/server/tools_runtime.py`
- `realai/training/__init__.py`
- `realai/training/build_datasets.py`
- `realai/training/eval.py`
- `realai/training/extract_from_agent_tools.py`
- `realai/training/finetune.py`
- `realai_good/realai/realai/realai_memory.json`
- `realai_good/realai/realai_memory.json`
- `realai_historical_backups/realai_versions_20260612/RealAIProject/realai/realai_memory.json`
- `realai_historical_backups/realai_versions_20260612/agent-tools-main/agent-tools-main/.vscode/mcp.json`
- `realai_historical_backups/realai_versions_20260612/agent-tools-main/agent-tools-main/.vscode/settings.json`
- `realai_historical_backups/realai_versions_20260612/real-fin/realai/realai - Copy/realai/realai_memory.json`
- `realai_historical_backups/realai_versions_20260612/real-fin/realai/realai - Copy/realai_memory.json`
- `realai_historical_backups/realai_versions_20260612/real-fin/realai/realai/realai_memory.json`
- `realai_historical_backups/realai_versions_20260612/real-fin/realai/realai_memory.json`
- `realai_memory/embodied_narratives/narrative_1780597611.json`
- `realai_memory/embodied_narratives/narrative_1780599365.json`
- `realai_memory/embodied_narratives/narrative_1780605682.json`
- `realai_memory/evolution_proposals.json`
- `realai_memory/hive_missions.json`
- `realai_memory/rag_memory_store.json`
- `realai_memory/workflow_runs_test.json`
- `realai_repo/realai-core/registry/package-lock.json`
- `realai_repo/realai-core__dup1/registry/package-lock.json`
- `realai_repo/realai/realai_memory.json`
- `realai_repo/realai__dup1/realai_memory.json`
- `realai_sdk/realai-core/registry/package-lock.json`
- `realai_sdk/realai-core__dup1/registry/package-lock.json`
- `realai_sdk/realai/realai_memory.json`
- `realai_sdk/realai__dup1/realai_memory.json`
- `src/components/VoiceFab.tsx`

## Priority content diffs (first 40)


## Hive recommendation (machine)

1. Promote priority uniques under agent-tools, agents, realai package if missing on authority
2. Review content diffs for newer gold (do not blind overwrite)
3. Ignore .venv / node_modules / egg-info noise
4. Full extract had gzip EOF — some tail files may be truncated
