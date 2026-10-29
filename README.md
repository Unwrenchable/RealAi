# RealAI

RealAI is a local-first AI hive: an orchestrator (`python -m realai.v3_orchestrator`, port `8001`) plus local GGUF models served by `llama-server` on Vulkan (port `8080`). On top of that it runs tools and agents, serves a browser console at `/console`, ships a VS Code extension (`apps/vscode/`) and a Next.js UI (`frontend/`).

There is also a separate cloud API, `python -m realai.api_server`, used for the Render deploy. It is its own server with its own routes and SQLite chat history; it does not proxy to the orchestrator. It reads `PORT` and defaults to `8001`, the same port as the orchestrator, so set `PORT` if you run both on one machine: `$env:PORT = 8000; python -m realai.api_server`.

**Product root:** the repo checkout (on the maintainer's machine, `C:\RealAI-clean`).  
**Git branch:** `main` (https://github.com/Unwrenchable/RealAi). The old `main` is `archive/main-legacy`.  
**Architecture contract:** [ARCHITECTURE.md](./ARCHITECTURE.md): v1 and v2 live *inside* this tree, not as version folders.  
**Recovery / history branches** are libraries; do not mega-merge them into `main`.

> **Source of truth:** [`realai/ability_catalog.py`](realai/ability_catalog.py) (LIVE / PARTIAL). If this README and the catalog disagree, the catalog wins. `ABILITIES.md` has the longer tool surface.

---

## What works today

Only abilities the catalog marks **LIVE** (64 of 78). Many are reached through `POST /v1/tools/execute`; the RackUp ones that go through `rackup_invoke` are for the RackUp pool app.

| Ability (catalog id) | How to reach it |
|---|---|
| Chat completion (`chat_completion`) | POST /v1/chat/completions |
| Text generation (`text_generation`) | POST /v1/chat/completions |
| Code generation (`code_generation`) | POST /v1/chat/completions (model) |
| Code execution (`code_execution`) | POST /v1/tools/execute (execute_code sandbox) |
| Embeddings (`embeddings`) | POST /v1/embeddings |
| Audio transcription (ASR) (`audio_transcription`) | POST /v1/audio/transcriptions + ability.audio_transcription (local Vosk) |
| Audio speech (TTS) (`audio_speech`) | POST /v1/audio/speech + ability.audio_speech (realai.voice / Windows SAPI / Kokoro) |
| Math solver (SymPy, verified) (`math_solver`) | ability.math_solver (sympy; solutions verified by substitution) |
| Data analysis (descriptive statistics) (`data_analysis`) | ability.data_analysis (stdlib statistics) |
| Translation (`translation`) | POST /v1/tools/execute ability.translation → local Hive chat |
| Web research & scraping (`web_research`) | POST /v1/tools/execute web_research |
| Task automation & infra ops (`task_automation`) | POST /v1/self-heal/* + tools self_heal_* |
| Voice interaction (streaming) (`voice_streaming`) | ability.voice_streaming oneshot (local TTS↔Hive chat) + optional WS |
| Business planning (`business_planning`) | POST /v1/tools/execute ability.business_planning → local Hive chat |
| Therapy & counseling (general conversation, not professional care) (`therapy_counseling`) | POST /v1/tools/execute ability.therapy_counseling → local Hive chat |
| Web3 integration (`web3_integration`) | POST /v1/tools/execute ability.web3_integration + core.tools.web3 |

### RackUp (pool app)

| Ability (catalog id) | How to reach it |
|---|---|
| RackUp professional coach (`coach`) | POST /v1/tools/execute ability.coach + rackup_invoke |
| Shot of the Day (`shot_of_the_day`) | POST /v1/tools/execute ability.shot_of_the_day + rackup_invoke |
| Post-match rating update (`rating_update`) | POST /v1/tools/execute ability.rating_update + rackup_invoke |
| Tournament / league insights (`tournament`) | POST /v1/tools/execute ability.tournament + rackup_invoke |
| ROC ledger audit (`ledger_audit`) | POST /v1/tools/execute ability.ledger_audit + rackup_invoke |
| Matchmaking advice (`matchmaking`) | POST /v1/tools/execute ability.matchmaking + rackup_invoke |
| Hall Context (`hall_context`) | POST /v1/tools/execute ability.hall_context + rackup_invoke |
| league validate (`league_validate`) | POST /v1/tools/execute ability.league_validate + rackup_invoke |
| moderation (`moderation`) | POST /v1/tools/execute ability.moderation + rackup_invoke |
| Money Anomaly (`money_anomaly`) | POST /v1/tools/execute ability.money_anomaly + rackup_invoke |
| payout sanity (`payout_sanity`) | POST /v1/tools/execute ability.payout_sanity + rackup_invoke |
| pyramid rules (`pyramid_rules`) | POST /v1/tools/execute ability.pyramid_rules + rackup_invoke |
| rating convert (`rating_convert`) | POST /v1/tools/execute ability.rating_convert + rackup_invoke |
| rating intel (`rating_intel`) | POST /v1/tools/execute ability.rating_intel + rackup_invoke |
| unified player card sync (`player_card_sync`) | POST /v1/tools/execute ability.player_card_sync + rackup_invoke |
| sotd contribute (`sotd_contribute`) | POST /v1/tools/execute ability.sotd_contribute + rackup_invoke |
| video analysis (`video_analysis`) | POST /v1/tools/execute ability.video_analysis + rackup_invoke |

### Desktop Lambda

| Ability (catalog id) | How to reach it |
|---|---|
| desktop lambda chat (`desktop_lambda_chat`) | POST /v1/tools/execute ability.desktop_lambda_chat |
| desktop lambda image (`desktop_lambda_image`) | POST /v1/tools/execute ability.desktop_lambda_image |
| desktop lambda video (`desktop_lambda_video`) | POST /v1/tools/execute ability.desktop_lambda_video |
| desktop lambda advanced (`desktop_lambda_advanced`) | POST /v1/tools/execute ability.desktop_lambda_advanced |

### Hive, tools and runtime

| Ability (catalog id) | How to reach it |
|---|---|
| overmind runner (`overmind_runner`) | POST /v1/tools/execute ability.overmind_runner |
| code engineer agent (`code_engineer_agent`) | POST /v1/tools/execute ability.code_engineer_agent |
| Deep promote (named roots + nests) (`deep_promote`) | abilities/deep_promote.py + craft /promote |
| Hierarchical Specialists (`hierarchical_specialists`) | POST /v1/tools/execute ability.hierarchical_specialists |
| approval_store (`approval_store`) | POST /v1/tools/execute ability.approval_store |
| device_selector (`device_selector`) | POST /v1/tools/execute device_selector + ability.device_selector |
| Code Engineer CLI (`code_engineer_cli`) | abilities/code_engineer_cli.py + realai.plugins.tools.code_engineer_cli |
| Harden repos (`harden_repos`) | abilities/harden_repos.py + realai.plugins.tools.harden_repos |
| Rollout all repos (`rollout_all_repos`) | abilities/rollout_all_repos.py + realai.plugins.tools.rollout_all_repos |
| Quarantine reconstruct (`quarantine_reconstruct`) | abilities/quarantine_reconstruct.py |
| Plugin system (`plugin_system`) | plugins/rackup_coach + POST tools rackup_invoke |
| Memory & persistent learning (`memory_learning`) | POST /v1/tools/execute ability.memory_learning + aura_memory + hive_memory + chat inject |
| Chain-of-thought + self-reflection (`self_reflection`) | POST /v1/self-improve/evaluate |
| Knowledge synthesis (`knowledge_synthesis`) | POST /v1/tools/execute ability.knowledge_synthesis + knowledge_graph + world_model |
| Multi-agent orchestration (`multi_agent`) | POST /v1/multi-agent/run + chat multi_agent=true + GET /v1/agents |
| Game-world integration (Atomic Fizz) (`game_world`) | POST tools game_world\|omnibrain\|world_brain + MCP vault77 |
| Atomic Fizz hive HTTP client (`atomic_fizz_hive_client`) | POST /v1/tools/execute ability.atomic_fizz_hive_client action=paths\|health\|chat |
| Console operator verify pack (`console_verify_pack`) | POST /v1/tools/execute ability.console_verify_pack |
| Synthetic organs hive (`organs_hive`) | POST tools organs_task + abilities/organs_hive.py |
| Observability, auditing, self-improvement (`observability_self_improve`) | POST /v1/tools/execute ability.observability_self_improve + /v1/self-heal/* + /v1/self-improve/* |
| Local inference (Vulkan / GGUF) (`local_inference`) | http://127.0.0.1:8080 via orchestrator |
| 9D / Ultimate Tic-Tac-Toe engine (MCTS) (`ttt9d_move`) | POST /v1/tools/execute {"name": "ttt9d_move", "arguments": {"state": {...}, "difficulty": "hard"}} |
| Recovered PEFT LoRA adapters (`lora_adapters`) | GET /v1/lora |
| Kilo-era gold recovery wiring (`kilo_recovery`) | GET /v1/recovery |
| Next.js operator UI (`frontend_ui`) | http://127.0.0.1:3000 |
| CLI surface (tools install) (`cli_surface`) | bin/realai*.cmd + realai.cli.craft |
| Hive governance (`hive_governance`) | POST /v1/tools/execute ability.hive_governance (local agents + coverage) |

## Partial abilities

These exist in some form but are not finished. Do not rely on them yet.

- **PARTIAL:** Image generation (`image_generation`)
- **PARTIAL:** Video generation (`video_generation`)
- **PARTIAL:** Image analysis (vision) (`image_analysis`)
- **PARTIAL:** realai-cli bridge (markets, rug-watch, paper trading) (`realai_cli_bridge`)
- **PARTIAL:** Git-learn (offline packet + coach stub) (`learn_git`)
- **PARTIAL:** Training + fine-tune pipeline (`training_pipeline`)
- **PARTIAL:** Chess engine (local Stockfish) (`chess_engine`)
- **PARTIAL:** PR triage (hive, read-only) (`pr_triage`)
- **PARTIAL:** Vulnerability triage (hive, read-only) (`vuln_triage`)
- **PARTIAL:** CI failure classifier (hive, read-only) (`ci_failure_classify`)
- **PARTIAL:** Synthetic organs runtime (organisms, curiosity, archeology) (`synthetic_organs_runtime`)
- **PARTIAL:** Self-evolving diagnose/critic/proposal loop (`self_evolving`)
- **PARTIAL:** Tool router heuristics (provider/cost/latency) (`tool_router_plugins`)
- **PARTIAL:** Workspace info / catalog (read-only, REALAI_HOME) (`workspace_info`)

Every catalog entry is currently LIVE or PARTIAL. (`_enrich_status_from_disk` can upgrade CODE or MISSING entries to GOLD at runtime; none exist today.)

---

## Surfaces

| Surface | What you get |
|---------|----------------|
| **Hive gateway** `:8001` | `python -m realai.v3_orchestrator` — chat, tools, agents, multi-agent, abilities, `/console` |
| **Vulkan llama-server** `:8080` | Local 7B GGUF (AMD RX 6700 XT / Vulkan) |
| **Console** | Browser home: `http://127.0.0.1:8001/console` (same UI as VS Code RealAI Console) |
| **VS Code / Cursor extension** | `apps/vscode` — RealAI Chat coder, foreign-repo mode, terminals, live abilities |
| **Next frontend** | `frontend/` — Vercel-ready UI shell (`NEXT_PUBLIC_API_URL` → API) |
| **Cloud API** | `python -m realai.api_server` — OpenAI-compatible API + SQLite chat history |
| **Voice** | XTTS / Voice Lab via gateway speech proxy (browser should hit `:8001`, not `:8890` directly) |
| **Any-repo** | Open another folder; Hive stays at product home — see `ANY_REPO.md` |

### API highlights (Hive / orchestrator)

```http
GET  /health
GET  /console
GET  /v1/tools
GET  /v1/agents
GET  /v1/capabilities
GET  /v1/hive
GET  /v1/abilities
POST /v1/chat/completions
POST /v1/agents/run
POST /v1/multi-agent/run
POST /v1/tools/execute
POST /v1/audio/speech
```

### Chat / console slash (local, deterministic)

- `/phase` `/where` — stage + host mode (product vs foreign) + stack
- `/patches` — `apps/vscode` auditor
- `/repo` — workspace listing
- `/tools` `/agents` `/multi` — via Craft / console Ops when stack is up

---

## Install

```powershell
git clone https://github.com/Unwrenchable/RealAi.git
cd RealAi
pip install -r requirements.txt
```

`pip install -e .` installs the package (Python 3.12+).

For local inference you also need a `llama-server` build with Vulkan and a GGUF model. The Next.js UI in `frontend/` needs Node.js and `pnpm`.

## Quick local start (Windows + Vulkan)

Tested on Windows with an AMD RX 6700 XT.

Paths below are examples (this machine uses `C:\RealAI-clean`; `start_v3_stack.ps1` assumes `C:\realai`). Adjust to your checkout.

```powershell
# 1) Vulkan model server (7B GGUF). -fa off is required on the RX 6700 XT (flash attention garbles output).
C:\llama-vulkan\llama-server.exe `
  -m "C:\models\checkpoints_lora\qwen2.5-coder-7b-instruct-q5_k_m.gguf" `
  --host 127.0.0.1 --port 8080 -ngl 99 -c 16384 -fa off --jinja

# 2) Hive gateway
cd C:\RealAI-clean
$env:PYTHONPATH = "C:\RealAI-clean;C:\RealAI-clean\realai"
$env:REALAI_VULKAN_BASE = "http://127.0.0.1:8080"
python -m realai.v3_orchestrator --host 127.0.0.1 --port 8001

# 3) Operator UI (Next.js) on http://127.0.0.1:3000
#    REALAI_API_BASE also works if NEXT_PUBLIC_API_URL is unset.
cd frontend
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8001"
pnpm install
pnpm dev
```

`scripts/start_v3_stack.ps1` runs the same stack but uses `-c 8192`. It binds `llama-server` to `127.0.0.1` unless `REALAI_LLAMA_HOST` is set.

Open **http://127.0.0.1:8001/console**

These commands bind `127.0.0.1`. The cloud API (`python -m realai.api_server`) binds `0.0.0.0` by default and has no `--host` option, so only run it on a trusted network or behind a firewall.

Optional helpers: `realai-stack`, `realai-health`, `realai-orch` — see `ANY_REPO.md`.

---

## Deploy (cloud)

Full instructions: **[DEPLOYMENT.md](./DEPLOYMENT.md)**

| Piece | Provider | Notes |
|-------|----------|--------|
| Frontend | **Vercel** | `frontend/` + root `vercel.json`; set `NEXT_PUBLIC_API_URL` |
| API (cloud) | **Render** | `render.yml` → `python -m realai.api_server` |
| Full GPU hive | **Your PC** | Vulkan + `v3_orchestrator` |
| Database | **SQLite** | `REALAI_DB_PATH` / `~/.realai/conversations.db` |

---

## Repo layout

One product. v1/v2 modules live inside these names — there is no `v1/` or `v2/` folder.

```
realai/                 Python package (hive gold in realai/orchestration/)
abilities/              Ability handlers
modules/organs/         Organs hive
frontend/               Next.js UI
apps/vscode/            Console extension
packages/               design-system + SDKs
scanners/               Promote / DDS tools (not runtime)
_quarantine/            Pointer to D:\ archive — do not merge dumps back
```

Full contract: **[ARCHITECTURE.md](./ARCHITECTURE.md)**  
Authority table: **[docs/AUTHORITY.md](./docs/AUTHORITY.md)**  
How v1/v2 are implemented: **[docs/LINEAGE.md](./docs/LINEAGE.md)**  
Physical tidy order: **[docs/REORG_PHASES.md](./docs/REORG_PHASES.md)**

---

## Docs index

| Doc | Purpose |
|-----|--------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Single-tree layout + lineage |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Vercel + Render + providers |
| [ABILITIES.md](./ABILITIES.md) | Ability / tool surface |
| [ANY_REPO.md](./ANY_REPO.md) | Use RealAI from any project folder |
| [QUICKSTART_LOCAL.md](./QUICKSTART_LOCAL.md) | Local quickstart |
| [docs/selfhost-provider.md](./docs/selfhost-provider.md) | Self-host declares `X-Provider: realai` |

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). When you add or change an ability, update its status in `realai/ability_catalog.py` in the same PR.

---

## License

See `LICENSE`.
