# RealAI API (FastAPI)

Minimal, OpenAI-compatible RealAI backend with `/v1/chat/completions` and `/v1/models`.

## Setup
1) Install dependencies (from repo root):
```bash
pip install -r requirements.txt
```
2) Set API keys (optional; falls back to built-ins):
```bash
export REALAI_API_KEYS="realai-dev,realai-demo,my-local-key"
```

## Run the server
```bash
uvicorn realai_api.app:app --reload --port 8000
```

## Example requests
List models:
```bash
curl -X GET http://localhost:8000/v1/models \
  -H "Authorization: Bearer realai-dev"
```

Chat completion:
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer realai-dev" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "realai-echo-1",
    "messages": [{"role": "user", "content": "Hello from RealAI"}]
  }'
```

## Where to plug future agents
- **Keys agent:** replace the hardcoded set in `realai_api/auth.py` with persistent storage.
- **Router agent:** extend `ProviderRouter` in `realai_api/providers.py` to pick providers/models intelligently.
- **Memory agent:** enrich `MockProvider.chat_completion` to read/write conversation state.
- **Tools agent:** add tool execution inside `MockProvider.chat_completion` or wrap it before returning the message.
