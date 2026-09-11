# Orchestrator :8001 — static bind readiness

## How to start (user action — do not auto-start from agents)

1. Ensure Vulkan llama-server is listening on `http://127.0.0.1:8080`.
2. From product home `C:\RealAI-clean\` run:

```bat
start_orchestrator.bat
```

Or:

```bat
set PYTHONPATH=C:\RealAI-clean;C:\RealAI-clean\realai
python -m realai.v3_orchestrator --host 127.0.0.1 --port 8001
```

Unified stack (Vulkan + orch + voice): `start_all.bat`.

Env alignment (7B / checkpoints_lora / CTX 65536):
- `REALAI_MODELS_DIR=C:\models\checkpoints_lora`
- `REALAI_LORA_ROOT=C:\models\checkpoints_lora`
- `REALAI_GGUF=C:\models\checkpoints_lora\qwen2.5-coder-7b-instruct-q5_k_m.gguf`
- `REALAI_CTX=65536`
- `REALAI_WORKSPACE` / `REALAI_HOME` / `REALAI_ROOT` → `C:\RealAI-clean\`
- `REALAI_API_BASE=http://127.0.0.1:8001`
- `REALAI_VULKAN_BASE=http://127.0.0.1:8080`

Logs directory: `C:\RealAI-clean\logs\` (marker `.wellkept`).

## Health URL

- Orchestrator: `http://127.0.0.1:8001/health` (also console at `/console`)
- Vulkan: `http://127.0.0.1:8080/health` (or models endpoint)

## What was fixed (static only)

- Package-root shims `realai\v3_orchestrator.py` and `realai\realai_orchestrator.py` hardened with `sys.path` insert for product home + package; re-export `main` from gold `realai.orchestration.v3_orchestrator`.
- Confirmed `realai\v3_runtime_bridge.py` package-root shim → gold `orchestration\v3_runtime_bridge.py` (hive OFF fix path).
- `start_orchestrator.bat` (repo root): added `REALAI_HOME`/`ROOT`/`WORKSPACE`, `REALAI_CTX=65536`, `REALAI_GGUF` 7B, logs mkdir note.
- `realai\scripts\start_orchestrator.bat`: fixed wrong `cd`/`PYTHONPATH` (was scripts dir); now cds to product home two levels up.
- Created `logs\.wellkept`.
- Import hole scan: all `from realai.*` modules referenced by gold v3 exist size>0; no dest-empty stubs required for bind.

## What still needs user restart

- User must start Vulkan `:8080` then orchestrator `:8001` (or `start_all.bat`).
- No agent heal/Craft operator/dispatch/training/`python -m realai` live start from this pass.
- If Craft previously fell back to Vulkan `:8080`, restart Craft after `:8001` is up so it prefers the hive orchestrator.

## Module resolution

- `-m realai.v3_orchestrator` → package-root shim → `orchestration.v3_orchestrator:main`
- Gold size ~136k at `realai\orchestration\v3_orchestrator.py`
- `orchestration\__init__.py` present (optional SDK imports guarded; `tts_routing` required and present)
