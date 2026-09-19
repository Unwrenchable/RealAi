# RealAI Ability Surface (Phase 5F)

Generated: `2026-09-19T17:49:53.974982+00:00`

**Coverage vs technical rundown:** **100.0%** weighted (64 LIVE, 0 PARTIAL, 0 CODE/GOLD/STUB, 0 MISSING/SOFT)

> `verify_v3_matrix` pass counts = stack health, not full product ability completeness.

## External gold roots (32/60 present)

- `OK` `C:\tools\realai` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\realai` — external_scan_roots_for_abilities
- `MISSING` `C:\Users\tsmit\realai\agent-tools\agent-tools-main` — external_scan_roots_for_abilities
- `MISSING` `C:\Users\tsmit\realai\archive\agent-tools-main` — external_scan_roots_for_abilities
- `MISSING` `C:\Users\tsmit\realai\agents` — external_scan_roots_for_abilities
- `MISSING` `C:\Users\tsmit\realai-clean` — external_scan_roots_for_abilities
- `MISSING` `C:\Users\tsmit\realai-clean\agents` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\realai_historical_backups` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\backups\realai-sync-20260508-090605` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\.realai` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\.agentx` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS` — external_scan_roots_for_abilities
- `MISSING` `C:\Users\tsmit\ATOMIC-FIZZ-CAPS-OLD` — external_scan_roots_for_abilities
- `MISSING` `C:\Users\tsmit\atomic-fizz-backup-2026-05-30` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS\backend\realai` — external_scan_roots_for_abilities
- `MISSING` `C:\Users\tsmit\ATOMIC-FIZZ-CAPS-OLD\ai\realai` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\Documents\GitHub\realai` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\Documents\GitHub\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS` — external_scan_roots_for_abilities
- `MISSING` `C:\Users\tsmit\OneDrive\Desktop\realai` — external_scan_roots_for_abilities
- `MISSING` `C:\Users\tsmit\OneDrive\Desktop\realai - Copy` — external_scan_roots_for_abilities
- `MISSING` `C:\Users\tsmit\OneDrive\Desktop\realai-cli` — external_scan_roots_for_abilities
- `MISSING` `C:\Users\tsmit\OneDrive\Desktop\realai-design-system` — external_scan_roots_for_abilities
- `MISSING` `C:\Users\tsmit\OneDrive\Desktop\realai-orchestration` — external_scan_roots_for_abilities
- `MISSING` `C:\Users\tsmit\OneDrive\Desktop\realai-sdk-js` — external_scan_roots_for_abilities
- `MISSING` `C:\Users\tsmit\OneDrive\Desktop\realai_agent` — external_scan_roots_for_abilities
- `MISSING` `C:\Users\tsmit\OneDrive\Desktop\realai_api` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\OneDrive\Apps\realai` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\AppData\Roaming\RealAi` — external_scan_roots_for_abilities
- `MISSING` `C:\Users\tsmit\realai\models\realai-1.0` — external_scan_roots_for_abilities
- `MISSING` `C:\Users\tsmit\realai\models\realai-overseer` — external_scan_roots_for_abilities
- `OK` `C:\Unwrenchable` — external_scan_roots_for_abilities
- `OK` `C:\temp` — external_scan_roots_for_abilities
- `OK` `C:\llama-vulkan` — external_scan_roots_for_abilities
- `OK` `C:\llama` — external_scan_roots_for_abilities
- `OK` `C:\$Recycle.Bin` — external_scan_roots_for_abilities
- `MISSING` `C:\realai\recovered\from_recycle_bin` — external_scan_roots_for_abilities
- `MISSING` `C:\realai\models` — external_scan_roots_for_abilities
- `OK` `C:\llama-vulkan\models` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\.cache\huggingface` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\.lmstudio` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\.openclaw` — external_scan_roots_for_abilities
- `MISSING` `C:\realai\recovered\from_users_dotfiles` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\AppData\Local\RealAI` — runtime_appdata
- `MISSING` `C:\Users\tsmit\realai\models\realai-embed` — gold_users_model_family
- `MISSING` `C:\Users\tsmit\Downloads\realai-main.zip` — gold_archive_files
- `MISSING` `C:\Users\tsmit\Downloads\realai-main (1).zip` — gold_archive_files
- `MISSING` `C:\Users\tsmit\Downloads\realai.zip` — gold_archive_files
- `OK` `C:\Users\tsmit\Downloads\realai_finetune_dataset.jsonl` — gold_archive_files
- `MISSING` `C:\Users\tsmit\realai.tar.gz` — gold_archive_files
- `OK` `C:\temp\realai_ui.html` — gold_archive_files
- `OK` `C:\llama.cpp` — inference_siblings
- `OK` `C:\models` — inference_siblings
- `OK` `C:\Users\tsmit\.realai\models` — assets_models
- `OK` `C:\Users\tsmit\models` — assets_models
- `OK` `C:\Users\tsmit\.ollama\models` — assets_models
- `MISSING` `C:\Users\tsmit\realai\agent-tools-main` — gold_agent_tools
- `MISSING` `C:\Users\tsmit\realai_historical_backups\realai_versions_20260612\agent-tools-main` — gold_agent_tools
- `OK` `C:\Unwrenchable\agent-tools` — gold_agent_tools
- `OK` `C:\Users\tsmit\.env.local` — gold_users_dotfiles
- `OK` `C:\Users\tsmit\.env.local.fizz` — gold_users_dotfiles

## C:\tools\realai CLI surface

- exists: **True**
- commands: realai-build, realai-chat, realai-code, realai-doctor, realai-gui, realai-heal, realai-health, realai-here, realai-improve, realai-local, realai-loop, realai-models, realai-orch, realai-promote, realai-selfheal, realai-server, realai-setup, realai-stack, realai-stop, realai-tools, realai-train, realai-voice, realai
- plugins: overseer, render, solana, trading

## Abilities

| ID | Name | Status | Live path |
|----|------|--------|-----------|
| `chat_completion` | Chat completion | **LIVE** | `POST /v1/chat/completions` |
| `text_generation` | Text generation | **LIVE** | `POST /v1/chat/completions` |
| `image_generation` | Image generation | **LIVE** | `POST /v1/tools/execute ability.image_generation (local Pillow PNG; no API key)` |
| `video_generation` | Video generation | **LIVE** | `POST /v1/tools/execute ability.video_generation (local animated GIF; no API key)` |
| `image_analysis` | Image analysis (vision) | **LIVE** | `POST /v1/tools/execute ability.image_analysis (local Pillow; no API key)` |
| `code_generation` | Code generation | **LIVE** | `POST /v1/chat/completions (model)` |
| `code_execution` | Code execution | **LIVE** | `POST /v1/tools/execute (execute_code sandbox)` |
| `embeddings` | Embeddings | **LIVE** | `POST /v1/embeddings` |
| `audio_transcription` | Audio transcription (ASR) | **LIVE** | `POST /v1/audio/transcriptions + ability.audio_transcription (local Vosk)` |
| `audio_speech` | Audio speech (TTS) | **LIVE** | `POST /v1/audio/speech + ability.audio_speech (realai.voice / Windows SAPI / Kokoro)` |
| `translation` | Translation | **LIVE** | `POST /v1/tools/execute ability.translation → local Hive chat` |
| `web_research` | Web research & scraping | **LIVE** | `POST /v1/tools/execute web_research` |
| `task_automation` | Task automation & infra ops | **LIVE** | `POST /v1/self-heal/* + tools self_heal_*` |
| `voice_streaming` | Voice interaction (streaming) | **LIVE** | `ability.voice_streaming oneshot (local TTS↔Hive chat) + optional WS` |
| `business_planning` | Business planning | **LIVE** | `POST /v1/tools/execute ability.business_planning → local Hive chat` |
| `therapy_counseling` | Therapy & counseling | **LIVE** | `POST /v1/tools/execute ability.therapy_counseling → local Hive chat` |
| `web3_integration` | Web3 integration | **LIVE** | `POST /v1/tools/execute ability.web3_integration + core.tools.web3` |
| `coach` | RackUp professional coach | **LIVE** | `POST /v1/tools/execute ability.coach + rackup_invoke` |
| `shot_of_the_day` | Shot of the Day | **LIVE** | `POST /v1/tools/execute ability.shot_of_the_day + rackup_invoke` |
| `rating_update` | Post-match rating update | **LIVE** | `POST /v1/tools/execute ability.rating_update + rackup_invoke` |
| `tournament` | Tournament / league insights | **LIVE** | `POST /v1/tools/execute ability.tournament + rackup_invoke` |
| `ledger_audit` | ROC ledger audit | **LIVE** | `POST /v1/tools/execute ability.ledger_audit + rackup_invoke` |
| `matchmaking` | Matchmaking advice | **LIVE** | `POST /v1/tools/execute ability.matchmaking + rackup_invoke` |
| `hall_context` | hall context | **LIVE** | `POST /v1/tools/execute ability.hall_context + rackup_invoke` |
| `league_validate` | league validate | **LIVE** | `POST /v1/tools/execute ability.league_validate + rackup_invoke` |
| `moderation` | moderation | **LIVE** | `POST /v1/tools/execute ability.moderation + rackup_invoke` |
| `money_anomaly` | money anomaly | **LIVE** | `POST /v1/tools/execute ability.money_anomaly + rackup_invoke` |
| `payout_sanity` | payout sanity | **LIVE** | `POST /v1/tools/execute ability.payout_sanity + rackup_invoke` |
| `pyramid_rules` | pyramid rules | **LIVE** | `POST /v1/tools/execute ability.pyramid_rules + rackup_invoke` |
| `rating_convert` | rating convert | **LIVE** | `POST /v1/tools/execute ability.rating_convert + rackup_invoke` |
| `rating_intel` | rating intel | **LIVE** | `POST /v1/tools/execute ability.rating_intel + rackup_invoke` |
| `player_card_sync` | unified player card sync | **LIVE** | `POST /v1/tools/execute ability.player_card_sync + rackup_invoke` |
| `sotd_contribute` | sotd contribute | **LIVE** | `POST /v1/tools/execute ability.sotd_contribute + rackup_invoke` |
| `video_analysis` | video analysis | **LIVE** | `POST /v1/tools/execute ability.video_analysis + rackup_invoke` |
| `desktop_lambda_chat` | desktop lambda chat | **LIVE** | `POST /v1/tools/execute ability.desktop_lambda_chat` |
| `desktop_lambda_image` | desktop lambda image | **LIVE** | `POST /v1/tools/execute ability.desktop_lambda_image` |
| `desktop_lambda_video` | desktop lambda video | **LIVE** | `POST /v1/tools/execute ability.desktop_lambda_video` |
| `desktop_lambda_advanced` | desktop lambda advanced | **LIVE** | `POST /v1/tools/execute ability.desktop_lambda_advanced` |
| `overmind_runner` | overmind runner | **LIVE** | `POST /v1/tools/execute ability.overmind_runner` |
| `code_engineer_agent` | code engineer agent | **LIVE** | `POST /v1/tools/execute ability.code_engineer_agent` |
| `deep_promote` | Deep promote (named roots + nests) | **LIVE** | `abilities/deep_promote.py + craft /promote` |
| `hierarchical_specialists` | hierarchical_specialists | **LIVE** | `POST /v1/tools/execute ability.hierarchical_specialists` |
| `approval_store` | approval_store | **LIVE** | `POST /v1/tools/execute ability.approval_store` |
| `device_selector` | device_selector | **LIVE** | `POST /v1/tools/execute device_selector + ability.device_selector` |
| `code_engineer_cli` | Code Engineer CLI | **LIVE** | `abilities/code_engineer_cli.py + realai.plugins.tools.code_engineer_cli` |
| `harden_repos` | Harden repos | **LIVE** | `abilities/harden_repos.py + realai.plugins.tools.harden_repos` |
| `rollout_all_repos` | Rollout all repos | **LIVE** | `abilities/rollout_all_repos.py + realai.plugins.tools.rollout_all_repos` |
| `quarantine_reconstruct` | Quarantine reconstruct | **LIVE** | `abilities/quarantine_reconstruct.py` |
| `plugin_system` | Plugin system | **LIVE** | `plugins/rackup_coach + POST tools rackup_invoke` |
| `learn_git` | Git-learn (offline packet + coach stub) | **LIVE** | `python -m realai.learn_git --all-branches + Craft /learn (no heal)` |
| `memory_learning` | Memory & persistent learning | **LIVE** | `POST /v1/tools/execute ability.memory_learning + aura_memory + hive_memory + chat inject` |
| `self_reflection` | Chain-of-thought + self-reflection | **LIVE** | `POST /v1/self-improve/evaluate` |
| `knowledge_synthesis` | Knowledge synthesis | **LIVE** | `POST /v1/tools/execute ability.knowledge_synthesis + knowledge_graph + world_model` |
| `multi_agent` | Multi-agent orchestration | **LIVE** | `POST /v1/multi-agent/run + chat multi_agent=true + GET /v1/agents` |
| `game_world` | Game-world integration (Atomic Fizz) | **LIVE** | `POST tools game_world|omnibrain|world_brain + MCP vault77` |
| `organs_hive` | Synthetic organs hive | **LIVE** | `POST tools organs_task + abilities/organs_hive.py` |
| `observability_self_improve` | Observability, auditing, self-improvement | **LIVE** | `POST /v1/tools/execute ability.observability_self_improve + /v1/self-heal/* + /v1/self-improve/*` |
| `local_inference` | Local inference (Vulkan / GGUF) | **LIVE** | `http://127.0.0.1:8080 via orchestrator` |
| `training_pipeline` | Training + fine-tune pipeline | **LIVE** | `GET /v1/training/* GET /v1/lora` |
| `lora_adapters` | Recovered PEFT LoRA adapters | **LIVE** | `GET /v1/lora` |
| `kilo_recovery` | Kilo-era gold recovery wiring | **LIVE** | `GET /v1/recovery` |
| `frontend_ui` | Next.js operator UI | **LIVE** | `http://127.0.0.1:3000` |
| `cli_surface` | CLI surface (tools install) | **LIVE** | `bin/realai*.cmd + realai.cli.craft (in-tree; not C:\tools\realai husk)` |
| `hive_governance` | Hive governance | **LIVE** | `POST /v1/tools/execute ability.hive_governance (local agents + coverage)` |

## Keyword learning

Discover / learn-keywords merges inventory tokens + CLI surface + rundown keywords + external roots into `scan_results/ability_keywords_learned.json` so DDS-3 ability scans go deeper each cycle. Self-improve training samples: `training/data/ability_surface.jsonl`.
