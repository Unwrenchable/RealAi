# How to run RealAI servers (one map)

**Product home (work here):** `C:\RealAI-clean`  
**Python package (import path):** `C:\RealAI-clean\realai\` — *not* a second product, *not* a nested git repo.

> Do **not** day-drive `C:\Users\tsmit\realai` — that tree still has `.git` and can diverge. Live Hive/agents/abilities we edit live under **RealAI-clean**.

## Ports (memorize)

| Port | Process | URL |
|------|---------|-----|
| **8080** | Vulkan `llama-server` | http://127.0.0.1:8080/health |
| **8001** | Hive `v3_orchestrator` | http://127.0.0.1:8001/health |
| **8890** | Voice Lab (optional) | http://127.0.0.1:8890/health |
| **5173** | TanStack Hive UI (optional) | http://127.0.0.1:5173 |

Hive also serves:

- Console → http://127.0.0.1:8001/console  
- Fusion UI → http://127.0.0.1:8001/fusion-ui/  
- Agents UI → http://127.0.0.1:8001/agents-ui/  

## Canonical start (pick one)

### A. Menu

```bat
cd /d C:\RealAI-clean
START_HERE.bat
```

PowerShell (no `/d` — that flag is cmd-only):

```powershell
cd C:\RealAI-clean
.\START_HERE.bat
```

### B. One-click full stack (recommended)

```bat
cd /d C:\RealAI-clean
start_all.bat
```

```powershell
cd C:\RealAI-clean
.\start_all.bat
```

Same as: `start_stack.bat`, `start_realai.bat`, `realai-stack` / `python -m realai stack`

### C. Pieces

| Need | Run |
|------|-----|
| GPU backend only | `start_realai_server.bat` |
| Hive only (Vulkan already up) | `start_orchestrator.bat` |
| Voice Lab | `realai\voice\start_voice_lab.bat` · PowerShell: `.\realai\voice\start_voice_lab.ps1` |
| Optional npm UI | `start_ui.bat` (after stack) |
| Stop stack | `realai-stop` or `python -m realai stack --stop` |

## Env contract

| Variable | Should be |
|----------|-----------|
| `REALAI_PRODUCT_ROOT` / `REALAI_WORKSPACE` | `C:\RealAI-clean` |
| `REALAI_HOME` | **Product root** `C:\RealAI-clean` (same as `start_all.bat`) |
| `PYTHONPATH` | `C:\RealAI-clean` (so `import realai` works) |
| `REALAI_API_BASE` | `http://127.0.0.1:8001` |
| `REALAI_VULKAN_BASE` | `http://127.0.0.1:8080` |

Legacy scripts that set `REALAI_HOME` to `...\realai` (the package) cause “lost” agents/abilities — Hive then looks under the wrong tree.

## Bat legend (aliases → canonical)

Root `start_*.bat` / `run_*.bat` names below still work from `C:\RealAI-clean`. Except `START_HERE.bat` (the menu) and the `start_stack.bat` / `start_realai.bat` aliases, the bodies live in `scripts\windows\` and the root file is a one-line forwarder.

| File | Role |
|------|------|
| **`START_HERE.bat`** | Menu — use this if unsure |
| **`start_all.bat`** | **Canonical** Vulkan+Hive (forwarder → `scripts\windows\start_all.bat`) |
| `start_stack.bat` / `start_realai.bat` | Alias → `start_all.bat` |
| `start_orchestrator.bat` | Hive `:8001` only (forwarder → `scripts\windows\start_orchestrator.bat` → `python -m realai.v3_orchestrator`) |
| `start_realai_server.bat` | Vulkan `:8080` only |
| `start_gpu_chat.bat` / `run_chat.bat` | Older full-stack variants (prefer `start_all`) |
| `start_ui.bat` | Optional frontend `:5173` |
| `logs\_launch_RealAI-*.bat` | Detached helpers used by `unified_stack.py` |

## Why `realai\` exists

```text
C:\RealAI-clean\                 ← product home (apps, abilities, agents, docs, bats)
C:\RealAI-clean\realai\          ← Python package (orchestrator, voice, craft, cli)
C:\Users\tsmit\realai\           ← OLD git clone — archive/reference only
```

Editing only under `Users\tsmit\realai` will **not** update the Hive you run from RealAI-clean.

## Health check

```bat
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8001/health
realai-health
```
