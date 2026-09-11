# Build RealAI With RealAI (Zero API Spend)

Goal: use **your machine** — local GGUF via Vulkan + orchestrator — to edit, test, and evolve this repo like a cloud coding agent, without paying per token.

**Repo:** `C:\RealAI-clean` (self-contained).

## 1. Start local inference

```powershell
cd C:\RealAI-clean

# Optional: promote/brand GGUFs under models/<id>/weights/
python -m realai.training.bootstrap_weights

# Preferred stack (Vulkan :8080 + orchestrator :8001)
realai-stack
# or:
# powershell -File scripts\run_local_chat.ps1 -SkipUI
```

Defaults:

```powershell
$env:REALAI_HOME = "C:\RealAI-clean"
$env:REALAI_API_URL = "http://127.0.0.1:8001"
$env:REALAI_DEFAULT_MODEL = "realai-default-coder"
```

## 2. Run the self-builder

```powershell
realai-build "Add a unit test for self_builder tool parsing"
# or
python -m realai.self_builder "Document the native GGUF pipeline"
# or closed loop (build + ingest training data):
realai-loop
start_self_build.bat
```

Model preference: **`realai-default-coder`** (qwen GGUF), then `realai-1.0-instruct`.

## Tools (workspace-scoped)

| Tool | Purpose |
| --- | --- |
| `read_file` | Read source before changing |
| `list_dir` | Explore the tree |
| `grep` | Find symbols and config |
| `search_replace` | Apply patches |
| `run_terminal_command` | Run tests / python -m |

Also available via orchestrator: `POST /v1/tools/execute`.

## 3. Training pipeline

```powershell
realai-train --stage status
realai-train --stage datasets
realai-train --stage plan
# finetune needs requirements-training.txt + GPU time
# realai-train --stage finetune --max-steps 50
realai-train --stage export
```

## 4. Docs

- `docs/REALAI_NATIVE_MODEL.md` — native GGUF ownership
- `ABILITIES.md` — full ability surface
