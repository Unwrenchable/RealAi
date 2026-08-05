# RealAI Skills Manifest

This document consolidates skill/capability information from:

- `docs/CAPABILITIES.md`
- `docs/model-manifest.md`
- `manifest.json`
- `realai/server/router.py`
- `realai/api_server.py` (authoritative runtime in this branch)

---

## 1) FusionUI

**Description:** Serves Fusion UI front-end and static assets as the authoritative root experience.

**Primary Entry Points:**
- `GET /`
- `GET /ui`
- `GET /index.html`
- `GET /script.js`
- `GET /style.css` (if present)

**Runtime Module:** `realai/api_server.py`

**Inputs:** HTTP path request

**Outputs:** HTML/JS/CSS/static content

---

## 2) HealthCheck

**Description:** Basic backend health verification.

**Primary Entry Point:**
- `GET /health`

**Runtime Module:** `realai/api_server.py`

**Outputs:**
```json
{"status":"ok"}
```

---

## 3) ChatCompletion

**Description:** Chat-style interaction endpoint compatible with OpenAI-like response shape.

**Primary Entry Point:**
- `POST /v1/chat/completions`

**Runtime Module:** `realai/api_server.py`
(Validation helpers reused from `realai/server/router.py`)

**Inputs:**
- `model` (optional)
- `messages[]` (required non-empty list with `{role, content}`)

**Outputs (stub mode):**
```json
{
  "id": "chatcmpl-realai-stub",
  "object": "chat.completion",
  "model": "realai-2.0",
  "choices": [
    {
      "index": 0,
      "message": {"role":"assistant","content":"Hello from RealAI stub"},
      "finish_reason":"stop"
    }
  ]
}
```

**Validation Behavior:**
- Invalid JSON body → HTTP 400
- Invalid/missing `messages` shape → HTTP 400

---

## 4) Embeddings

**Description:** Embedding generation endpoint using structured router implementation.

**Primary Entry Point:**
- `POST /v1/embeddings`

**Runtime Module:** `realai/server/router.py` via `handle_embeddings_request`

**Inputs:**
- `model` (optional, defaults from settings)
- `input` string or string list (required)

**Outputs:**
- OpenAI-like list embedding structure (`object`, `data[]`, `embedding`)

---

## 5) ModelRegistry

**Description:** Lists available model metadata.

**Primary Entry Point:**
- `GET /v1/models`

**Runtime Module:** `realai/server/router.py` via `handle_models_list`

**Outputs:**
- `{ "object": "list", "data": [...] }`

---

## 6) Providers

**Description:** Lists configured providers.

**Primary Entry Point:**
- `GET /v1/providers`

**Runtime Module:** `realai/server/router.py` via `handle_providers_list`

**Outputs:**
- `{ "object": "list", "data": [...] }`

---

## 7) Tasks (Minimal Queue Stub)

**Description:** Accepts task submissions in minimal queued form for Fusion-compatible clients.

**Primary Entry Point:**
- `POST /v1/tasks`

**Runtime Module:** `realai/api_server.py`

**Inputs:**
- `task` (required string)
- `context` (optional)

**Outputs:**
```json
{
  "id":"task-<timestamp>",
  "task":"<name>",
  "status":"queued",
  "context":"..."
}
```

---

## 8) LlamaBackend (Backend-Only Role)

**Description:** Local llama backend/inference stack available in structured modules and broader repo.

**Important Policy in this branch:**
- Llama backend is treated as backend capability, **not the main launcher**.
- Authoritative launcher is `realai_server.py` → `realai/api_server.py`.

---

## 9) Tooling/Capability Skill Surfaces (Reference)

From `docs/CAPABILITIES.md`, broader RealAI capabilities include:
- code generation/execution
- image/video/audio operations
- translation
- web research
- memory & learning
- multi-agent orchestration
- plugin system
- web3 integrations

These may be surfaced through other runtime layers beyond the minimal authoritative server used here.

---

## Authoritative Entrypoint Contract

Default entrypoint script:
- `realai_server.py`

Server module:
- `realai/api_server.py`

Default bind:
- `REALAI_HOST=127.0.0.1`
- `REALAI_PORT=8000`

Environment defaults set by launcher:
- `REALAI_DEFAULT_UI=fusion`
- `REALAI_UI_PATH=fusion-ui`
- `REALAI_SKIP_AUTH=true`
- `REALAI_CLEAN_STUB=true`
