# RealAI Boot Gate Report

**Date:** 2026-07-13  
**Command:** `python -m realai.api_server --host 127.0.0.1 --port 8000`  
**Status:** **SERVER UP** — API surface responds; local inference not fully wired

## Pass matrix

| Endpoint | Result | Notes |
|----------|--------|-------|
| Process start | **PASS** | Imports clean; binds 127.0.0.1:8000 |
| `GET /health` | **PASS** 200 | `{"status":"healthy","model":"realai-2.0"}` |
| `GET /v1/models` | **PASS** 200 | 9 models listed (realai + cloud ids) |
| `GET /v1/models/realai-2.0` | **PASS** 200 | Full metadata |
| `GET /v1/capabilities` | **PASS** 200 | capability_graph present |
| `GET /ui/providers` | **PASS** 200 | openai, anthropic, grok, … |
| `GET /` (UI) | expected | Chat UI HTML served (not fully exercised) |
| `POST /v1/chat/completions` | **PASS** 200 | Placeholder: *no local model configured* |
| `POST /v1/embeddings` | **PASS** 200 | Returns zero-vector stub (not real embed model) |
| `GET /v1/status` | **FAIL** 404 | Not implemented on this handler |

## First real blockers (priority order)

### 1. Local model not registered / loaded (blocks real chat)

Chat returns:

> Local RealAI is selected, but no local model is configured/loaded yet.  
> Register a local model and set it as default_llm, then retry.

GGUF *files* exist under `models/` (Llama-3.2-1B, Qwen2.5-coder, realai-1.0-instruct) but sizes are **~1.5–1.8 MB** — far too small for real 1B/7B Q4 weights (usually hundreds of MB). Treat them as **stubs/placeholders** until full weights are present. They are also **not** registered as `default_llm`.

**Fix direction:** (1) obtain real GGUF weights, (2) register via local model registry / `realai.toml` and set `default_llm`, or (3) call API with Bearer key + `X-Provider` for cloud.

### 2. Embeddings are stub zeros (blocks RAG/memory quality)

`/v1/embeddings` returns a vector of `0.0` values quickly (~650ms).  
Matches known gap: missing real embedding backend (`sentence_transformers` / local embed model).

**Fix direction:** wire `realai-embed` or sentence-transformers; return non-zero dims consistently.

### 3. Single-threaded `HTTPServer` (operational risk)

First concurrent probe saw chat/embeddings **timeout** while server was busy — stdlib `HTTPServer` is one-request-at-a-time.  
Fine for boot proof; not fine for UI + API together under load.

**Fix direction (later):** ThreadingHTTPServer or uvicorn/FastAPI path if present in apps/api.

### 4. `/v1/status` missing

Minor OpenAI-compat / client expectation gap (VS Code client may call it).

## What this means for unification

| Goal | Boot gate says |
|------|----------------|
| “Does RealAI run?” | **Yes** — clean package boots |
| “Can it answer for real?” | **Not yet** without local model or API key |
| “Did archive recovery help boot?” | Indirect — SDK/agentx recovered; server path already clean |
| Next work | Local GGUF registration → real chat; then embeddings |

## How to re-run

```powershell
cd C:\realai
python -m realai.api_server --host 127.0.0.1 --port 8000

# separate terminal
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8000/v1/models -UseBasicParsing
```

Leave the server running for UI: http://127.0.0.1:8000/
