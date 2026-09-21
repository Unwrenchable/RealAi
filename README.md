# RealAI

Local-first AI hive: GPU chat (Vulkan), multi-agent orchestration, tools, voice, and a console UI that also runs in VS Code.

**Canonical product root:** `C:\RealAI-clean`  
**Live Git branch:** `live/realai-clean-20260911` → https://github.com/Unwrenchable/RealAi  
**Architecture contract:** [ARCHITECTURE.md](./ARCHITECTURE.md) — v1 and v2 live *inside* this tree, not as version folders.  
**Recovery / history branches** on GitHub are libraries — do not mega-merge them into live.

---

## What it is (current abilities)

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

### Ability catalog (honesty map)

See `realai/ability_catalog.py` and `ABILITIES.md`. Trust LIVE / PARTIAL / STUB in the catalog over marketing lists.

---

## Quick local stack (Windows GPU)

```powershell
# 1) Vulkan model server (7B GGUF, high context)
C:\llama-vulkan\llama-server.exe `
  -m "C:\models\checkpoints_lora\qwen2.5-coder-7b-instruct-q5_k_m.gguf" `
  --host 127.0.0.1 --port 8080 -ngl 99 -c 65536

# 2) Hive gateway
cd C:\RealAI-clean
$env:PYTHONPATH = "C:\RealAI-clean;C:\RealAI-clean\realai"
$env:REALAI_VULKAN_BASE = "http://127.0.0.1:8080"
python -m realai.v3_orchestrator --host 127.0.0.1 --port 8001
```

Open **http://127.0.0.1:8001/console**

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

## License

See `LICENSE`.
