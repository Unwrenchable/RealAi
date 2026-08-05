# Recovery + wiring (2026-07-15)

## What was promoted / wired

### Live modules

| Module | Path | Role |
|--------|------|------|
| Embeddings handler | `realai/lambda_embeddings_audio.py` | Local OpenAI-ish embeddings (deterministic default) |
| Local llama client | `realai/providers/local_llama.py` | Vulkan `:8080` chat/completion client |
| Recovery registry | `realai/recovery_registry.py` | Inventory, LoRA list, promote helper |
| realai_agent pack | `realai/realai_agent/` | Desktop agent pack (already present) |
| policy / sanity | `agent-tools-main/policy.json`, `sanity_check.py` | From realai2 |

### Orchestrator endpoints (`:8001`)

| Method | Path | Status |
|--------|------|--------|
| GET | `/health` | 200 even if Vulkan down (`status=degraded`) |
| GET | `/v1/recovery` | Kilo/realai2 inventory |
| GET | `/v1/lora` | **110** PEFT adapters from `checkpoints_lora` |
| POST | `/v1/embeddings` | **LIVE** (64-d deterministic / ST if installed) |
| POST | `/v1/audio/transcriptions` | STUB |
| POST | `/v1/audio/speech` | STUB |
| POST | `/v1/recovery/promote` | Re-run promote |
| GET | `/v1/models` | Includes `realai-embeddings` + `realai-lora-*` |
| GET | `/v1/capabilities` | Embeddings LIVE; LoRA GOLD; ~**46%** weighted |

### LoRA gold

- **Root:** `C:\Users\tsmit\.grok\worktrees\tsmit-realai\realai2\checkpoints_lora`
- **Count:** 110 adapters (Qwen2.5-1.5B-Instruct base, r=16)
- **Catalog:** `scan_results/lora_adapters.json`
- **Not auto-merged** into Vulkan — listed for finetune tooling

### Do not overwrite

`promote_core` will **not** clobber adapted `lambda_embeddings_audio.py` or larger live server modules with raw Lambda stubs.

## Verify (Windows — preferred)

```powershell
# Full stack
powershell -File C:\realai\scripts\start_v3_stack.ps1

curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/v1/recovery
curl http://127.0.0.1:8001/v1/lora
curl -X POST http://127.0.0.1:8001/v1/embeddings `
  -H "Content-Type: application/json" `
  -d "{\"input\":\"hello\",\"model\":\"realai-embeddings\"}"
curl -X POST http://127.0.0.1:8001/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d "{\"model\":\"realai-default-coder\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":32}"
```

### E2E proven (2026-07-16)

| Check | Result |
|-------|--------|
| Vulkan `:8080` | `{"status":"ok"}` (bound `0.0.0.0`) |
| Orch `:8001` | `status=ok`, `vulkan.ok=true` |
| Embeddings | deterministic 64-d |
| Chat | returned `RealAI online` via `realai-default-coder` |
| LoRA | 110 adapters |
| Live modules | 9/9 |
| Coverage | ~46% weighted honesty |

## Start

```powershell
# Recommended one-shot (Windows)
powershell -File C:\realai\scripts\start_v3_stack.ps1
```

Or manually:

```text
C:\llama-vulkan\llama-server.exe -m C:\realai\models\qwen2.5-coder-7b-instruct-q5_k_m.gguf --host 0.0.0.0 --port 8080 -c 8192 -ngl 99 --jinja
cd C:\realai
set REALAI_VULKAN_BASE=http://127.0.0.1:8080
set REALAI_SELF_IMPROVE=true
python -m realai.v3_orchestrator --host 127.0.0.1 --port 8001
```

**WSL note:** WSL `127.0.0.1` is not Windows localhost. Point orch at the Windows host gateway (from `ip route` default), e.g. `REALAI_VULKAN_BASE=http://192.168.144.1:8080`, or run the stack on Windows.
