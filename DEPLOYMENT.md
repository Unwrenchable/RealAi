# RealAI deployment guide

How to run and ship **frontend**, **backend**, **model providers**, and the **database**.

Canonical tree: `C:\RealAI-clean`  
Live branch: `live/realai-clean-20260911`

There are **two backends**:

1. **Hive gateway (full product)** — `python -m realai.v3_orchestrator` on `:8001`  
   Needs local Vulkan (`:8080`) for GPU coding hive. **Not** suitable for Vercel. Best on your Windows GPU box (or a fat GPU VM).
2. **Cloud API** — `python -m realai.api_server`  
   OpenAI-compatible HTTP + SQLite history. Fits **Render** / any Python host. Uses **cloud provider keys** (OpenAI, Anthropic, Grok, ...) and/or whatever local backends you wire.

Frontend:

3. **Next UI** — `frontend/` on **Vercel** (or `next dev` locally)  
4. **Console** — `http://127.0.0.1:8001/console` when Hive is up (preferred local UX)

---

## Table of contents

1. [Architecture](#architecture)
2. [Prerequisites](#prerequisites)
3. [Environment variables](#environment-variables)
4. [Providers (model keys)](#providers-model-keys)
5. [Database (SQLite)](#database-sqlite)
6. [Local full stack (GPU hive)](#local-full-stack-gpu-hive)
7. [Frontend on Vercel](#frontend-on-vercel)
8. [Backend on Render](#backend-on-render)
9. [Wire Vercel to Render](#wire-vercel-to-render)
10. [VS Code / Cursor extension](#vs-code--cursor-extension)
11. [Smoke checks](#smoke-checks)
12. [Troubleshooting](#troubleshooting)

---

## Architecture

```
Browser / VS Code Chat
        |
        +--(local)--> :8001  v3_orchestrator --> :8080 Vulkan GGUF
        |                    +-- /console, /v1/*, voice proxy
        |
        +--(cloud)--> Vercel (frontend/)
                           |
                           +-- NEXT_PUBLIC_API_URL
                                 |
                                 +--> Render realai.api_server
                                        +-- SQLite conversations.db
                                        +-- Provider APIs (OpenAI, ...)
```

**Do not** expect Vercel to run Vulkan, XTTS, or the full multi-agent hive. Deploy UI to Vercel; keep GPU hive on the PC (or deploy only the lighter `api_server` to Render).

---

## Prerequisites

### Local GPU hive (Windows)

- Python **3.11+**
- `C:\RealAI-clean` on `PYTHONPATH`
- Vulkan `llama-server` (e.g. `C:\llama-vulkan\llama-server.exe`)
- GGUF weights under `C:\models\checkpoints_lora\` (default 7B coder Q5)
- Node 20+ / npm (frontend + extension builds)
- Optional: pnpm (Vercel install uses pnpm from lockfile)

### Cloud

- GitHub repo access: `Unwrenchable/RealAi`
- Vercel account
- Render account (or any host that runs Python 3.11 + `requirements.txt`)
- At least one provider API key if you are not using local Vulkan behind a tunnel

---

## Environment variables

Copy from `.env.example` and `frontend/.env.example`. Prefer dashboard secrets over committing `.env`.

### Frontend (Vercel / Next)

| Variable | Required | Meaning |
|----------|----------|---------|
| `NEXT_PUBLIC_API_URL` | **Yes (prod)** | Public API base, e.g. `https://realai-api.onrender.com` — **never** `127.0.0.1` on Vercel |
| `REALAI_API_BASE` | optional | Same as above for server-side routes |
| `REALAI_API_KEY` | optional | If API expects a bearer |

### Hive / local orchestrator

| Variable | Default / example | Meaning |
|----------|-------------------|---------|
| `PYTHONPATH` | `C:\RealAI-clean;C:\RealAI-clean\realai` | Import `realai` |
| `REALAI_VULKAN_BASE` | `http://127.0.0.1:8080` | llama-server |
| `REALAI_HOME` | `C:\RealAI-clean` | Product home |
| `REALAI_WORKSPACE` | cwd | Foreign-repo workspace |
| `REALAI_MODELS_DIR` | `C:\models\checkpoints_lora` | Weights root |
| `PORT` | `8001` | Gateway bind |

### Cloud API (`realai.api_server`) / Render

| Variable | Meaning |
|----------|---------|
| `OPENAI_API_KEY` / `REALAI_OPENAI_API_KEY` | OpenAI |
| `REALAI_ANTHROPIC_API_KEY` | Anthropic |
| `REALAI_GROK_API_KEY` | xAI Grok |
| `REALAI_GEMINI_API_KEY` | Gemini |
| `REALAI_OPENROUTER_API_KEY` | OpenRouter |
| `REALAI_MISTRAL_API_KEY` | Mistral |
| `REALAI_TOGETHER_API_KEY` | Together |
| `REALAI_DEEPSEEK_API_KEY` | DeepSeek |
| `REALAI_PERPLEXITY_API_KEY` | Perplexity |
| `REALAI_MODEL` | Default model id (e.g. `realai-1.0`) |
| `CORS_ALLOWED_ORIGINS` | Comma list incl. your `*.vercel.app` |
| `ENV` | `production` |
| `WEB_CONCURRENCY` | `1` recommended on free tiers |
| `PORT` | Provided by host |
| `REALAI_DB_PATH` | SQLite file path |
| `REALAI_DATA_DIR` | Parent dir for default DB (`~/.realai`) |
| `REALAI_VULKAN_BASE` | Local llama-server base (default `http://127.0.0.1:8080`) |
| `REALAI_VULKAN_FORWARD` | `auto` (default) / `off` — proxy chat to Vulkan when healthy |

Provider keys can also be sent per-request as `Authorization: Bearer ...` (prefix auto-detect) or `X-Provider` / `X-Base-URL` overrides — see `realai/api_server.py`.

---

## Providers (model keys)

### Local (GPU hive)

Configured in `config/amd_inference.yaml` + env:

- Backend: **Vulkan llama.cpp** (not CUDA on the AMD box)
- Default GGUF: `qwen2.5-coder-7b-instruct-q5_k_m.gguf`
- Context: use `-c 65536` on llama-server for long Chat sessions
- VS Code setting: `realai.contextTokens` default **65536**

`providers.yaml` also lists cloud providers (`openai`, `anthropic`, ...) — enable + set `*_API_KEY` env when you want cloud fallbacks.

### Cloud API path

Set one or more `REALAI_*_API_KEY` / `OPENAI_API_KEY` on Render.  
Clients call the same OpenAI-style `/v1/chat/completions` surface.

---

## Database (SQLite)

`realai.api_server` uses **SQLite** (no Postgres required for default deploy).

**Default path:** `%USERPROFILE%\.realai\conversations.db`  
(or `$REALAI_DATA_DIR/conversations.db`)

**Override:**

```powershell
$env:REALAI_DB_PATH = "D:\data\realai\conversations.db"
```

**Schema (auto-created on boot):**

```sql
users (
  id INTEGER PRIMARY KEY,
  external_id TEXT UNIQUE NOT NULL,  -- key:<hash> or anon:<ip>
  created_at INTEGER
);

chat_messages (
  id INTEGER PRIMARY KEY,
  user_external_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at INTEGER
);
```

**Render note:** free/ephemeral disks lose SQLite on restart. For durable chat history either:

- Attach a **persistent disk** and set `REALAI_DB_PATH` onto it, or
- Accept ephemeral history, or
- Later wire Postgres (not required for first deploy)

Hive orchestrator memory/tools may use additional local stores under the product tree; treat GPU hive state as **machine-local** unless you deliberately back it up.

---

## Local full stack (GPU hive)

### 1. Vulkan

```powershell
C:\llama-vulkan\llama-server.exe `
  -m "C:\models\checkpoints_lora\qwen2.5-coder-7b-instruct-q5_k_m.gguf" `
  --host 127.0.0.1 --port 8080 -ngl 99 -c 65536
```

### 2. Orchestrator

```powershell
cd C:\RealAI-clean
$env:PYTHONPATH = "C:\RealAI-clean;C:\RealAI-clean\realai"
$env:REALAI_VULKAN_BASE = "http://127.0.0.1:8080"
python -m realai.v3_orchestrator --host 127.0.0.1 --port 8001
```

### 3. Open console

http://127.0.0.1:8001/console

### 4. Optional Next UI against local Hive

```powershell
cd C:\RealAI-clean\frontend
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8001"
npm install
npm run dev
```

### 5. Optional cloud-style API locally

```powershell
cd C:\RealAI-clean
$env:PYTHONPATH = "C:\RealAI-clean;C:\RealAI-clean\realai"
python -m realai.api_server
```

---

## Frontend on Vercel

Config is already fixed for `frontend/` (not `apps/frontend`):

- Root `vercel.json` — `pnpm --filter realai-frontend build`, output `frontend/.next`
- `pnpm-workspace.yaml` includes `frontend`
- `frontend/vercel.json` for Root Directory = `frontend`

### Dashboard steps

1. Import **Unwrenchable/RealAi**
2. Branch: **`live/realai-clean-20260911`**
3. Root Directory: **repo root** (recommended) *or* `frontend`
4. Framework: Next.js (detected)
5. Env → Production:
   - `NEXT_PUBLIC_API_URL` = your Render URL (https)
6. Deploy

### CLI steps

```powershell
cd C:\RealAI-clean
npm i -g vercel   # once
vercel login
vercel            # preview
vercel --prod     # production
```

### Build smoke (local)

```powershell
cd C:\RealAI-clean\frontend
npm run build
```

---

## Backend on Render

`render.yml` / `render.yaml` define service **realai-api**:

- Build: `pip install -r requirements.txt`
- Start: `python -m realai.api_server`
- Health: `/health`

### Dashboard steps

1. New → Web Service → connect `Unwrenchable/RealAi`
2. Branch: `live/realai-clean-20260911`
3. Runtime: Python 3.11
4. Build / start as above (or Blueprint from `render.yml`)
5. Set env:
   - `OPENAI_API_KEY` (or other provider keys)
   - `REALAI_MODEL`
   - `CORS_ALLOWED_ORIGINS=https://<your-app>.vercel.app,https://your.domain`
   - `ENV=production`
   - `WEB_CONCURRENCY=1`
   - Optional: `REALAI_DB_PATH` on a persistent disk
6. Health check path: `/health`
7. Deploy

### CORS

Your Vercel origin **must** appear in `CORS_ALLOWED_ORIGINS` or browser chat will fail.

---

## Wire Vercel to Render

1. Note Render URL: `https://realai-api.onrender.com` (example)
2. Vercel env: `NEXT_PUBLIC_API_URL=https://realai-api.onrender.com`
3. Redeploy frontend
4. Confirm browser Network tab calls that host (not `:8890` / not localhost)

For **full Hive** from a hosted UI you need a public tunnel or GPU VM exposing `:8001` (Tailscale, Cloudflare Tunnel, etc.) — Render's `api_server` is the supported lightweight cloud API.

---

## VS Code / Cursor extension

```powershell
cd C:\RealAI-clean\apps\vscode
# after compile/package:
# realai-vscode-1.2.15.vsix (or newer)
```

Install the VSIX into **both** VS Code and Cursor if you use both hosts.  
Settings of note:

- `realai.contextTokens` → match llama `-c` (65536)
- `realai.productHome` → `C:\RealAI-clean`
- `realai.chatDispatchAgents` → coder/agent Chat posts `/v1/agents/run`

Foreign repo: open another folder; `/phase` should report `host foreign` without Hive health-fluff multi.

---

## Smoke checks

```powershell
# Local hive
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/v1/tools
# Console
start http://127.0.0.1:8001/console

# Cloud API (after Render)
curl https://YOUR-API.onrender.com/health
```

Frontend: open the Vercel URL → chat once → DevTools Network should show `NEXT_PUBLIC_API_URL` host only.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Vercel build looks for `apps/frontend` | Use latest `live/realai-clean-20260911` (path fix landed) |
| Chat on Vercel hits localhost | Set `NEXT_PUBLIC_API_URL` to https API and redeploy |
| CORS errors | Add Vercel origin to Render `CORS_ALLOWED_ORIGINS` |
| SQLite empty after Render restart | Ephemeral disk — add persistent disk + `REALAI_DB_PATH` |
| Hive chat is health fluff in foreign repo | Update extension ≥ 1.2.15; use `/phase` local slash |
| SPEAK calls `:8890` in browser | Use console via `:8001` proxy only |
| Vulkan OOM / token faults | 7B GGUF + `-ngl 99` + high `-c`; prefer XTTS over fighting LLM VRAM |
| Vercel opens `http://127.0.0.1:8001/console` | Fixed on live branch: `frontend/app/page.tsx` must not hard-redirect; set `NEXT_PUBLIC_API_URL` on Vercel |
| Render shows old chat dashboard at `/` | Set `REALAI_PUBLIC_UI_URL=https://realaiui.vercel.app` and redeploy; old UI at `/legacy-ui` |
| `pnpm` missing locally | `npx pnpm@9 install` — Vercel still uses lockfile |

---

## Related docs

- [README.md](./README.md) — product overview + abilities
- [ABILITIES.md](./ABILITIES.md) — tools / abilities map
- [ANY_REPO.md](./ANY_REPO.md) — portable CLI
- [frontend/.env.example](./frontend/.env.example)
- [.env.example](./.env.example)

