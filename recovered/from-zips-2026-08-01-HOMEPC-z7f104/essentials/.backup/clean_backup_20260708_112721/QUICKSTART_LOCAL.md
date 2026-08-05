# 🚀 RealAI Local Structured Server - Quick Reference

## ⚡ Quick Start (3 Commands)

```powershell
# 1. (Optional) Download llama-cli.exe from https://github.com/ggerganov/llama.cpp/releases

# 2. (Optional) Download a GGUF model if you want llama-cli or llama.cpp execution

# 3. Start server
python -m realai.server.app
```

## 📝 Configuration Files

| File | Purpose | Example |
|------|---------|---------|
| `realai.toml` | Server config | See `realai.toml.example` |
| `models.yaml` | Model registry | Edit the structured registry entries here |
| `providers.yaml` | Provider registry | Enable and configure providers here |

## 🔧 Essential Commands

```powershell
# Check setup
python scripts/setup_local_llama.py

# Start server (basic)
python -m realai.server.app

# Start server (FastAPI with reload)
uvicorn realai.server.app:app --host 127.0.0.1 --port 8000 --reload

# Test endpoint
curl http://127.0.0.1:8000/health

# List models
curl http://127.0.0.1:8000/v1/models

# List providers
curl http://127.0.0.1:8000/v1/providers
```

## 🎯 API Usage

### Python (requests)
```python
import requests

response = requests.post(
	'http://127.0.0.1:8000/v1/chat/completions',
	json={
		'model': 'realai-1.0',
		'messages': [{'role': 'user', 'content': 'Hello!'}]
	}
)
print(response.json()['choices'][0]['message']['content'])
```

### Python (OpenAI-compatible)
```python
from openai import OpenAI

client = OpenAI(
	base_url="http://127.0.0.1:8000/v1",
	api_key="local"
)

response = client.chat.completions.create(
	model="realai-1.0",
	messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

### cURL
```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
	"model": "realai-1.0",
	"messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## 🗂️ Model Registry Example

```yaml
models:
  - id: realai-1.0
    type: chat
    provider: local
    backend: realai-fallback
    path: realai-2.0
    context_length: 8192

  - id: realai-embed
    type: embedding
    provider: local
    backend: deterministic
    embedding_dimensions: 64
```

## 📍 File Locations

```
realai/
├── realai.toml                    # Server configuration
├── models.yaml                    # Structured model registry
├── providers.yaml                 # Structured provider registry
├── realai/
│   └── server/
│       ├── app.py                 # Server entrypoint
│       ├── router.py              # HTTP route dispatcher
│       ├── config.py              # Typed config loader
│       ├── backends.py            # Backend resolver
│       ├── providers.py           # Provider registry
│       └── llama_cli_backend.py   # Optional llama-cli backend
├── docs/
│   ├── local-llama-setup.md       # Complete setup guide
│   └── LOCAL_LLAMA_README.md      # Overview & benefits
└── apps/
    └── frontend/                  # Next.js web client
```

## 🔍 Troubleshooting Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| "llama-cli not found" | Install llama.cpp binaries or use the default fallback backends |
| "Model file not found" | Check `models.yaml` and the configured model path |
| Slow inference | Use Q4_K_M quantization, enable GPU |
| Out of memory | Use smaller model or Q3_K_M quantization |
| Server won't start | Check `realai.toml`, `models.yaml`, and `providers.yaml` |

## 📚 Documentation

- **Complete Setup**: `docs/local-llama-setup.md`
- **Overview**: `docs/LOCAL_LLAMA_README.md`
- **Backend config**: `realai.toml`, `models.yaml`, `providers.yaml`
- **Frontend**: `apps/frontend/README.md`

## 🎨 Recommended Models

| Model | Size | Use Case | Download |
|-------|------|----------|----------|
| Llama 3.2 3B (Q4_K_M) | ~2GB | Fast responses | [Link](https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF) |
| Llama 3.1 7B (Q4_K_M) | ~4GB | Quality responses | [Link](https://huggingface.co/bartowski/Meta-Llama-3.1-7B-Instruct-GGUF) |
| Mistral 7B (Q4_K_M) | ~4GB | Instruction following | [Link](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF) |
| DeepSeek Coder 6.7B | ~4GB | Code generation | [Link](https://huggingface.co/TheBloke/deepseek-coder-6.7B-instruct-GGUF) |

## 🎯 Success Checklist

- [ ] `realai.toml` configured if you need custom defaults
- [ ] `models.yaml` contains the models you want to expose
- [ ] `providers.yaml` reflects the providers you want enabled
- [ ] Server starts without errors
- [ ] `/health` endpoint returns `"status": "ok"`
- [ ] `/v1/models` returns the registered models
- [ ] `/v1/providers` returns provider health/status
- [ ] Chat completion request returns response
- [ ] Optional provider credentials are set if you want hosted models

## 🔗 Quick Links

- **llama.cpp releases**: https://github.com/ggerganov/llama.cpp/releases
- **GGUF models**: https://huggingface.co/models?search=gguf
- **RealAI GitHub**: https://github.com/Unwrenchable/realai

---

**Need help?** Start with `/health`, `/v1/models`, and `/v1/providers` to verify the structured server state.
