# RealAI

RealAI is a **local-first AI platform monorepo** built around a structured Python backend, a Next.js chat frontend, and shared SDK/CLI surfaces. The current implementation focuses on a stable platform core: chat and embeddings APIs, model and provider registries, durable memory and task state, and local deployment.

## Current state

The repository now has a working platform nucleus:

- **Structured backend** in `realai\server\` with OpenAI-style endpoints
- **Durable memory and task state** backed by SQLite
- **Model and provider registries** loaded from `models.yaml` and `providers.yaml`
- **Python SDK + CLI** aligned to the structured backend
- **Next.js frontend** in `apps\frontend` that builds against the same API contract
- **TypeScript SDK + CLI** packages for monorepo consumers

Some docs and code still describe the larger target vision. The most accurate runtime source of truth is:

- `realai\server\app.py`
- `realai\server\router.py`
- `realai\server\config.py`
- `models.yaml`
- `providers.yaml`

## Platform surfaces

| Surface | Purpose | Key paths |
| --- | --- | --- |
| Backend | Structured inference, memory, tasks, models, providers, tools, health, metrics | `realai\server\*` |
| Legacy shim | Backward-compatible API/web UI path | `realai\api_server.py`, `api_server.py` |
| Frontend | Next.js chat application | `apps\frontend\*` |
| Python SDK | Structured HTTP client | `realai\sdk\python\realai_client.py` |
| Python CLI | Structured CLI commands | `realai\cli\realai_cli.py` |
| TS SDK | TypeScript client package | `packages\sdk-ts\src\index.ts` |
| TS CLI | TypeScript command-line client | `packages\cli\src\index.ts` |

## Implemented HTTP API

The structured backend currently exposes:

- `POST /v1/chat/completions`
- `POST /v1/embeddings`
- `GET /v1/models`
- `GET /v1/models/{id}`
- `GET /v1/providers`
- `GET /v1/providers/{id}`
- `POST /v1/memory/store`
- `POST /v1/memory/inspect`
- `POST /v1/memory/clear`
- `POST /v1/tasks`
- `GET /v1/tasks`
- `GET /v1/tasks/{id}`
- `GET /v1/tools`
- `GET /health`
- `GET /metrics`

## Quick start

### Python backend

```bash
git clone https://github.com/Unwrenchable/realai.git
cd realai
pip install -e .
python -m realai.server.app
```

The server listens on `http://127.0.0.1:8000` by default.

### Frontend

```bash
pnpm install
pnpm --filter realai-frontend dev
```

### Python SDK

```python
from realai.sdk.python.realai_client import RealAIClient

client = RealAIClient(api_url="http://127.0.0.1:8000")

health = client.health()
models = client.models()
reply = client.chat(
    model="realai-1.0",
    messages=[{"role": "user", "content": "Hello"}],
)
```

### CLI

```bash
python -m realai.cli.realai_cli health
python -m realai.cli.realai_cli models
python -m realai.cli.realai_cli providers
python -m realai.cli.realai_cli chat "Summarize the platform"
```

## Configuration

The structured backend uses:

- `realai.toml` for server defaults
- `models.yaml` for model registry entries
- `providers.yaml` for provider registry entries

The default local models currently registered are:

- `realai-1.0`
- `realai-overseer`
- `realai-embed`

## Local architecture

```text
Browser / CLI / SDK
        |
        v
   Structured API
  realai.server.app
        |
        +--> model registry (models.yaml)
        +--> provider registry (providers.yaml)
        +--> SQLite persistence
        |      - memory
        |      - tasks
        |
        +--> backend resolver
               - deterministic embeddings fallback
               - RealAI local fallback
               - optional vLLM / llama.cpp / llama-cli
```

## Notes

- `docs\architecture.md` is still partly a target-state blueprint, but now includes a clearer distinction between the implemented platform and the longer roadmap.
- `QUICKSTART_LOCAL.md` is the best reference for local structured-server setup.
- `apps\frontend\README.md` covers the web app and deployment path.
