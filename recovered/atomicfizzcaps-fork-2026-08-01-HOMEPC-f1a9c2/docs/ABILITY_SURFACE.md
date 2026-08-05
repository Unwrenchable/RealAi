# RealAI Ability Surface (Phase 5F)

Generated: `2026-07-16T17:59:22.587154+00:00`

**Coverage vs technical rundown:** **46.0%** weighted (7 LIVE, 8 PARTIAL, 12 CODE/GOLD/STUB, 4 MISSING/SOFT)

> `verify_v3_matrix` pass counts = stack health, not full product ability completeness.

## External gold roots (60/60 present)

- `OK` `C:\tools\realai` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\realai` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\realai\agent-tools\agent-tools-main` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\realai\archive\agent-tools-main` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\realai\agents` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\realai-clean` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\realai-clean\agents` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\realai_historical_backups` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\backups\realai-sync-20260508-090605` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\.realai` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\.agentx` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\ATOMIC-FIZZ-CAPS-OLD` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\atomic-fizz-backup-2026-05-30` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS\backend\realai` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\ATOMIC-FIZZ-CAPS-OLD\ai\realai` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\Documents\GitHub\realai` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\Documents\GitHub\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\OneDrive\Desktop\realai` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\OneDrive\Desktop\realai - Copy` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\OneDrive\Desktop\realai-cli` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\OneDrive\Desktop\realai-design-system` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\OneDrive\Desktop\realai-orchestration` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\OneDrive\Desktop\realai-sdk-js` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\OneDrive\Desktop\realai_agent` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\OneDrive\Desktop\realai_api` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\OneDrive\Apps\realai` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\AppData\Roaming\RealAi` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\realai\models\realai-1.0` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\realai\models\realai-overseer` — external_scan_roots_for_abilities
- `OK` `C:\Unwrenchable` — external_scan_roots_for_abilities
- `OK` `C:\temp` — external_scan_roots_for_abilities
- `OK` `C:\llama-vulkan` — external_scan_roots_for_abilities
- `OK` `C:\llama` — external_scan_roots_for_abilities
- `OK` `C:\$Recycle.Bin` — external_scan_roots_for_abilities
- `OK` `C:\realai\recovered\from_recycle_bin` — external_scan_roots_for_abilities
- `OK` `C:\realai\models` — external_scan_roots_for_abilities
- `OK` `C:\llama-vulkan\models` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\.cache\huggingface` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\.lmstudio` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\.openclaw` — external_scan_roots_for_abilities
- `OK` `C:\realai\recovered\from_users_dotfiles` — external_scan_roots_for_abilities
- `OK` `C:\Users\tsmit\AppData\Local\RealAI` — runtime_appdata
- `OK` `C:\Users\tsmit\realai\models\realai-embed` — gold_users_model_family
- `OK` `C:\Users\tsmit\Downloads\realai-main.zip` — gold_archive_files
- `OK` `C:\Users\tsmit\Downloads\realai-main (1).zip` — gold_archive_files
- `OK` `C:\Users\tsmit\Downloads\realai.zip` — gold_archive_files
- `OK` `C:\Users\tsmit\Downloads\realai_finetune_dataset.jsonl` — gold_archive_files
- `OK` `C:\Users\tsmit\realai.tar.gz` — gold_archive_files
- `OK` `C:\temp\realai_ui.html` — gold_archive_files
- `OK` `C:\llama.cpp` — inference_siblings
- `OK` `C:\models` — inference_siblings
- `OK` `C:\Users\tsmit\.realai\models` — assets_models
- `OK` `C:\Users\tsmit\models` — assets_models
- `OK` `C:\Users\tsmit\.ollama\models` — assets_models
- `OK` `C:\Users\tsmit\realai\agent-tools-main` — gold_agent_tools
- `OK` `C:\Users\tsmit\realai_historical_backups\realai_versions_20260612\agent-tools-main` — gold_agent_tools
- `OK` `C:\Unwrenchable\agent-tools` — gold_agent_tools
- `OK` `C:\Users\tsmit\.env.local` — gold_users_dotfiles
- `OK` `C:\Users\tsmit\.env.local.fizz` — gold_users_dotfiles

## C:\tools\realai CLI surface

- exists: **True**
- commands: chat, help, image, research, system, video, web3
- plugins: overseer, render, solana, trading

## Abilities

| ID | Name | Status | Live path |
|----|------|--------|-----------|
| `chat_completion` | Chat completion | **LIVE** | `POST /v1/chat/completions` |
| `text_generation` | Text generation | **LIVE** | `POST /v1/chat/completions` |
| `image_generation` | Image generation | **STUB** | `—` |
| `video_generation` | Video generation | **STUB** | `—` |
| `image_analysis` | Image analysis (vision) | **CODE** | `—` |
| `code_generation` | Code generation | **LIVE** | `POST /v1/chat/completions (model)` |
| `code_execution` | Code execution | **PARTIAL** | `POST /v1/tools/execute` |
| `embeddings` | Embeddings | **LIVE** | `POST /v1/embeddings` |
| `audio_transcription` | Audio transcription (ASR) | **STUB** | `POST /v1/audio/transcriptions` |
| `audio_speech` | Audio speech (TTS) | **STUB** | `POST /v1/audio/speech` |
| `translation` | Translation | **SOFT** | `POST /v1/chat/completions (model)` |
| `web_research` | Web research & scraping | **GOLD** | `—` |
| `task_automation` | Task automation & infra ops | **PARTIAL** | `POST /v1/self-heal/*` |
| `voice_streaming` | Voice interaction (streaming) | **MISSING** | `—` |
| `business_planning` | Business planning | **SOFT** | `—` |
| `therapy_counseling` | Therapy & counseling | **SOFT** | `—` |
| `web3_integration` | Web3 integration | **GOLD** | `—` |
| `plugin_system` | Plugin system | **CODE** | `—` |
| `memory_learning` | Memory & persistent learning | **PARTIAL** | `chat memory inject (REALAI_MEMORY_INJECT)` |
| `self_reflection` | Chain-of-thought + self-reflection | **PARTIAL** | `POST /v1/self-improve/evaluate` |
| `knowledge_synthesis` | Knowledge synthesis | **PARTIAL** | `—` |
| `multi_agent` | Multi-agent orchestration | **PARTIAL** | `POST /v1/multi-agent/run + chat multi_agent=true + GET /v1/agents` |
| `game_world` | Game-world integration (Atomic Fizz) | **GOLD** | `—` |
| `observability_self_improve` | Observability, auditing, self-improvement | **PARTIAL** | `/v1/self-improve/* /v1/self-heal/*` |
| `local_inference` | Local inference (Vulkan / GGUF) | **LIVE** | `http://127.0.0.1:8080 via orchestrator` |
| `training_pipeline` | Training + fine-tune pipeline | **PARTIAL** | `GET /v1/training/* GET /v1/lora` |
| `lora_adapters` | Recovered PEFT LoRA adapters | **GOLD** | `GET /v1/lora` |
| `kilo_recovery` | Kilo-era gold recovery wiring | **LIVE** | `GET /v1/recovery` |
| `frontend_ui` | Next.js operator UI | **LIVE** | `http://127.0.0.1:3000` |
| `cli_surface` | CLI surface (tools install) | **GOLD** | `—` |
| `hominis_enterprise` | Hominis enterprise stack | **GOLD** | `—` |

## Keyword learning

Discover / learn-keywords merges inventory tokens + CLI surface + rundown keywords + external roots into `scan_results/ability_keywords_learned.json` so DDS-3 ability scans go deeper each cycle. Self-improve training samples: `training/data/ability_surface.jsonl`.
