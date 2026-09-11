# RealAI-clean — local chat (working stack)

## Architecture

```
UI :3000  →  orchestrator :8001  →  Vulkan llama-server :8080
```

- **Repo:** `C:\RealAI-clean` (this clean clone)
- **Old messy tree:** `C:\realai` — leave it; do not scan/dump here

## Portable: use RealAI in *any* project

See **[ANY_REPO.md](ANY_REPO.md)**. Full toolkit is on PATH after:

```powershell
powershell -ExecutionPolicy Bypass -File C:\RealAI-clean\scripts\install_global.ps1
# new terminal:
cd C:\YourProject
realai-tools          # map of all global commands
realai                # chat here
realai-code "fix it"
realai-stack          # GPU + orch + UI (once per session)
realai-heal
```

## Root launchers (repo root)

| File | What it does |
|------|----------------|
| `run_chat.bat` / `start_gpu_chat.bat` | Full stack: Vulkan `:8080` + orchestrator `:8001` + UI `:3000` |
| `run_selfheal.bat` | Stack + curated promote + verify |
| `start_realai_server.bat` | Vulkan llama-server only (`:8080`) |
| `start_orchestrator.bat` | Orchestrator only (`:8001`; needs Vulkan up) |
| `realai.cmd` | `python -m realai …` (doctor, chat, serve) |
| `python realai_local_server.py` | Lightweight llama-cli API on `:8000` (legacy shim) |
| `python realai_gui.py` | Desktop GUI (defaults to orchestrator `:8001`) |

## One command (Windows PowerShell)

```powershell
cd C:\RealAI-clean
powershell -ExecutionPolicy Bypass -File C:\RealAI-clean\scripts\run_local_chat.ps1
```

Or double-click / run:

```bat
run_chat.bat
start_gpu_chat.bat
```

Opens:

| Piece | URL |
|-------|-----|
| **Start** | `START_HERE.bat` / `start_all.bat` — see [`docs/RUN_SERVERS.md`](docs/RUN_SERVERS.md) |
| Chat UI (optional npm) | http://127.0.0.1:5173 (`start_ui.bat`) |
| Fusion UI (Hive-served) | http://127.0.0.1:8001/fusion-ui/ |
| Agent Activity UI (Hive-served) | http://127.0.0.1:8001/agents-ui/ |
| Console (Hive-served) | http://127.0.0.1:8001/console |
| Orchestrator health | http://127.0.0.1:8001/health |
| Vulkan health | http://127.0.0.1:8080/health |

First UI run runs `npm install` in `apps\frontend` (once).

### Models (this repo)

Default chat weight:

`models\qwen2.5-coder-7b-instruct-q5_k_m.gguf` → public id **`realai-default-coder`**

Also on disk under `models\`:

- `realai-1.0-instruct-Q4_K_M.gguf`
- `Llama-3.2-1B-Instruct-Q4_K_M.gguf` (+ aliases)
- Catalog: `config\realai_models.json` (rebuilt by orchestrator / `model_catalog`)

Vulkan binary: `C:\llama-vulkan\llama-server.exe`

### Self-heal / curated promote

```powershell
# start stack + apply allowlist promote + verify
powershell -ExecutionPolicy Bypass -File C:\RealAI-clean\scripts\run_local_selfheal.ps1

# or
scripts\run_local_selfheal.bat
```

### CLI entry

```bat
realai.cmd doctor
python -m realai
```

## Backend only

```powershell
powershell -ExecutionPolicy Bypass -File C:\RealAI-clean\scripts\run_local_chat.ps1 -SkipUI
```

Vulkan only (no orchestrator):

```bat
start_realai_server.bat
```

Manual chat test:

```powershell
curl http://127.0.0.1:8001/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d "{\"model\":\"realai-default-coder\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":64}"
```

## What was brought over from C:\realai

| Path | Why |
|------|-----|
| `realai/v3_orchestrator.py` | Chat proxy + tools + health |
| `realai/model_catalog.py` | realai-* → GGUF mapping |
| `realai/self_heal.py` | optional self-heal API |
| `realai/deepen_cycle.py` | optional deepen |
| `realai/plugins/tools/device_selector.py` | soft torch |
| `agents/agentx/agents.json` | multi-agent list |
| `scripts/run_local_chat.ps1` | start stack |
| `apps/frontend/src/lib/*` | missing chat client (recreated) |

Already in clean (kept): GGUF under `models\`, `aura_memory`, `memory/engine`, frontend UI components.

## Do not

- Run discover/scan dump loops into `recovered/` (72k+ junk files already there — ignore)
- Point UI at raw `:8080` — use orchestrator `:8001`
- Keep developing in `C:\realai`

## Cold-archive recovered mess (optional, later)

```powershell
# Prefer Windows Python so paths stay on C:\realai-cold
cd C:\RealAI-clean
python scripts\cold_archive_recovered.py
```
