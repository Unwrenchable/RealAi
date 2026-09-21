# Quarantine unique-file delta (2026-09-21)

Compare: `_quarantine/twins_20260921` + `twins_20260921_b` vs live gold
(`realai/orchestration`, `realai/plugins`, `realai/core`, `modules/organs`, `abilities`, `apps/vscode`, `frontend`).
Match key: **basename** only. Verdict: CANDIDATE (unique + organ/plugin/ability/orch-like), STAY (duplicate or unclear), SKIP (locks/jsonl/css/tsx).

- Rows scanned (py + skip markers): **150**
- Verdict counts: `{'SKIP': 2, 'STAY': 138, 'CANDIDATE': 10}`
- Unique CANDIDATE basenames: **10**

## Candidates (unique basename)

| quarantine_path | basename | live_hit | verdict | suggested live dest |
|-----------------|----------|----------|---------|---------------------|
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin___init___18.py` | `plugin___init___18.py` | | CANDIDATE | `realai/plugins/plugin___init___18.py` |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin___init___32.py` | `plugin___init___32.py` | | CANDIDATE | `realai/plugins/plugin___init___32.py` |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin___init___70.py` | `plugin___init___70.py` | | CANDIDATE | `realai/plugins/plugin___init___70.py` |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin___init___84.py` | `plugin___init___84.py` | | CANDIDATE | `realai/plugins/plugin___init___84.py` |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin_plugin_marketplace_27.py` | `plugin_plugin_marketplace_27.py` | | CANDIDATE | `realai/plugins/plugin_plugin_marketplace_27.py` |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin_plugin_marketplace_79.py` | `plugin_plugin_marketplace_79.py` | | CANDIDATE | `realai/plugins/plugin_plugin_marketplace_79.py` |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin_sample_plugin_17.py` | `plugin_sample_plugin_17.py` | | CANDIDATE | `realai/plugins/plugin_sample_plugin_17.py` |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin_sample_plugin_69.py` | `plugin_sample_plugin_69.py` | | CANDIDATE | `realai/plugins/plugin_sample_plugin_69.py` |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin_test_realai_39.py` | `plugin_test_realai_39.py` | | CANDIDATE | `realai/plugins/plugin_test_realai_39.py` |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin_test_realai_8.py` | `plugin_test_realai_8.py` | | CANDIDATE | `realai/plugins/plugin_test_realai_8.py` |

## Sample STAY (duplicates / unclear) — first 80

| quarantine_path | basename | live_hit | verdict | suggested live dest |
|-----------------|----------|----------|---------|---------------------|
| `_quarantine/twins_20260921/realai__grok_export_realai/RealAI-clean/archive/__init__.py` | `__init__.py` | `realai/orchestration/__init__.py` | STAY |  |
| `_quarantine/twins_20260921/realai__grok_export_realai/RealAI-clean/scan_results/__init__.py` | `__init__.py` | `realai/orchestration/__init__.py` | STAY |  |
| `_quarantine/twins_20260921/realai__grok_export_realai/RealAI-clean/training/build_datasets.py` | `build_datasets.py` | `realai/plugins/build_datasets.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__C_realai_plugins/__init__.py` | `__init__.py` | `realai/orchestration/__init__.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/ability_catalog.py` | `ability_catalog.py` | `realai/plugins/ability_catalog.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/api_big_server.py` | `api_big_server.py` | `realai/plugins/api_big_server.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/api_server.py` | `api_server.py` | `realai/plugins/api_server.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/api_server_backup.py` | `api_server_backup.py` | `realai/plugins/api_server_backup.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/api_server_cpu.py` | `api_server_cpu.py` | `realai/plugins/api_server_cpu.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/build_datasets.py` | `build_datasets.py` | `realai/plugins/build_datasets.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/chat_qwen_lora_directml.py` | `chat_qwen_lora_directml.py` | `realai/plugins/chat_qwen_lora_directml.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/client.py` | `client.py` | `realai/plugins/client.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/coach.py` | `coach.py` | `realai/plugins/coach.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/coach_agent.py` | `coach_agent.py` | `realai/plugins/coach_agent.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/create_training_runs_json.py` | `create_training_runs_json.py` | `realai/plugins/create_training_runs_json.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/device_selector.py` | `device_selector.py` | `realai/plugins/device_selector.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/extract_agent_tool_data.py` | `extract_agent_tool_data.py` | `realai/plugins/extract_agent_tool_data.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/games.py` | `games.py` | `realai/plugins/games.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/glicko2.py` | `glicko2.py` | `realai/plugins/glicko2.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/hall_context.py` | `hall_context.py` | `realai/plugins/hall_context.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/lambda_advanced.py` | `lambda_advanced.py` | `realai/plugins/lambda_advanced.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/lambda_chat.py` | `lambda_chat.py` | `realai/plugins/lambda_chat.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/lambda_core.py` | `lambda_core.py` | `realai/plugins/lambda_core.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/lambda_core_shared.py` | `lambda_core_shared.py` | `realai/plugins/lambda_core_shared.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/lambda_embeddings_audio.py` | `lambda_embeddings_audio.py` | `realai/plugins/lambda_embeddings_audio.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/lambda_image.py` | `lambda_image.py` | `realai/plugins/lambda_image.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/lambda_video.py` | `lambda_video.py` | `realai/plugins/lambda_video.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/leagues.py` | `leagues.py` | `realai/plugins/leagues.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/league_validate.py` | `league_validate.py` | `realai/plugins/league_validate.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/ledger_audit.py` | `ledger_audit.py` | `realai/plugins/ledger_audit.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/local_models.py` | `local_models.py` | `realai/plugins/local_models.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/main.py` | `main.py` | `realai/plugins/main.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/matchmaking.py` | `matchmaking.py` | `realai/plugins/matchmaking.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/moderation.py` | `moderation.py` | `realai/plugins/moderation.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/money_anomaly.py` | `money_anomaly.py` | `realai/plugins/money_anomaly.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/money_audit.py` | `money_audit.py` | `realai/plugins/money_audit.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/mypy_plugin.py` | `mypy_plugin.py` | `realai/plugins/mypy_plugin.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/organs_bridge.py` | `organs_bridge.py` | `realai/plugins/organs_bridge.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/payout_sanity.py` | `payout_sanity.py` | `realai/plugins/payout_sanity.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin.py` | `plugin.py` | `realai/plugins/plugin.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin_marketplace.py` | `plugin_marketplace.py` | `realai/plugins/plugin_marketplace.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin_memory.py` | `plugin_memory.py` | `realai/plugins/plugin_memory.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin_plugin_marketplace.py` | `plugin_plugin_marketplace.py` | `realai/plugins/plugin_plugin_marketplace.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin_registry_builder.py` | `plugin_registry_builder.py` | `realai/plugins/plugin_registry_builder.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin_sample_plugin.py` | `plugin_sample_plugin.py` | `realai/plugins/plugin_sample_plugin.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin_test_realai.py` | `plugin_test_realai.py` | `realai/plugins/plugin_test_realai.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin___init__.py` | `plugin___init__.py` | `realai/plugins/plugin___init__.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/pyramid.py` | `pyramid.py` | `realai/plugins/pyramid.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/pyramid_rules.py` | `pyramid_rules.py` | `realai/plugins/pyramid_rules.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/pytest_plugin.py` | `pytest_plugin.py` | `realai/plugins/pytest_plugin.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/rating_convert.py` | `rating_convert.py` | `realai/plugins/rating_convert.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/rating_intel.py` | `rating_intel.py` | `realai/plugins/rating_intel.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/rating_update.py` | `rating_update.py` | `realai/plugins/rating_update.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/realai_architect_agent.py` | `realai_architect_agent.py` | `realai/plugins/realai_architect_agent.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/realai_full_autonomous.py` | `realai_full_autonomous.py` | `realai/plugins/realai_full_autonomous.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/realai_gui.py` | `realai_gui.py` | `realai/plugins/realai_gui.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/realai_local_server.py` | `realai_local_server.py` | `realai/plugins/realai_local_server.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/realai_rebuilder.py` | `realai_rebuilder.py` | `realai/plugins/realai_rebuilder.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/realai_self_improving_agent.py` | `realai_self_improving_agent.py` | `realai/plugins/realai_self_improving_agent.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/registry.py` | `registry.py` | `realai/plugins/registry.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/roc.py` | `roc.py` | `realai/plugins/roc.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/sample_plugin.py` | `sample_plugin.py` | `realai/plugins/sample_plugin.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/self_improvement.py` | `self_improvement.py` | `realai/plugins/self_improvement.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/self_improving_agent.py` | `self_improving_agent.py` | `realai/plugins/self_improving_agent.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/setup.py` | `setup.py` | `realai/plugins/setup.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/shot_of_the_day.py` | `shot_of_the_day.py` | `realai/plugins/shot_of_the_day.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/smart_merge_realai.py` | `smart_merge_realai.py` | `realai/plugins/smart_merge_realai.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/sotd_contribute.py` | `sotd_contribute.py` | `realai/plugins/sotd_contribute.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/sotd_library.py` | `sotd_library.py` | `realai/plugins/sotd_library.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/test_local_server.py` | `test_local_server.py` | `realai/plugins/test_local_server.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/tournament.py` | `tournament.py` | `realai/plugins/tournament.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/train_directml.py` | `train_directml.py` | `realai/plugins/train_directml.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/train_from_agent_manifests.py` | `train_from_agent_manifests.py` | `realai/plugins/train_from_agent_manifests.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/train_qwen_directml.py` | `train_qwen_directml.py` | `realai/plugins/train_qwen_directml.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/train_qwen_lora_directml.py` | `train_qwen_lora_directml.py` | `realai/plugins/train_qwen_lora_directml.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/types.py` | `types.py` | `realai/plugins/types.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/video_analysis.py` | `video_analysis.py` | `realai/plugins/video_analysis.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/_hypothesis_plugin.py` | `_hypothesis_plugin.py` | `realai/plugins/_hypothesis_plugin.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/_loader.py` | `_loader.py` | `realai/plugins/_loader.py` | STAY |  |
| `_quarantine/twins_20260921/realai__plugins__plugins/_schema_validator.py` | `_schema_validator.py` | `realai/plugins/_schema_validator.py` | STAY |  |
| … | … | … | STAY | (58 more omitted) |

## SKIP markers

Count: 2
- `_quarantine/twins_20260921/globals.css`
- `_quarantine/twins_20260921/layout.tsx`

## Promote decision (this pass)

**Promoted: none.**

The 10 CANDIDATE basenames are nested-dump renames under ealai__plugins__plugins/ (plugin___init___N.py, plugin_sample_plugin_N.py, plugin_test_realai_N.py, plugin_plugin_marketplace_N.py). They are not Type-A clear missing organs/plugins/abilities/orch helpers. Live already has sample_plugin.py and real plugins under ealai/plugins/. Leave them in quarantine.

Organs under 	wins_20260921_b/realai__imports/.../organs/ matched live basenames → STAY (duplicates).
