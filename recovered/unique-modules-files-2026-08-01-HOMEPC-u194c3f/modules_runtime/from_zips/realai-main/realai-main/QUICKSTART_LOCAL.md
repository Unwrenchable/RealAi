# 🚀 RealAI Local Llama.cpp - Quick Reference

## ⚡ Quick Start (3 Commands)

```powershell
# 1. Download llama-cli.exe from https://github.com/ggerganov/llama.cpp/releases

# 2. Download a GGUF model (e.g., Llama 3.2 3B Q4_K_M) to C:\Users\tsmit\models\

# 3. Start server
python -m realai.server.app
```

## 📝 Configuration Files

| File | Purpose | Example |
|------|---------|---------|
| `realai.toml` | Server config | See `realai.toml.example` |
| `realai/models/registry.json` | Model registry | See `registry.json.example` |

## 🔧 Essential Commands

```powershell
# Check setup
python scripts/setup_local_llama.py

# Start server (basic)
python -m realai.server.app

# Start server (FastAPI with reload)
uvicorn realai.server.app:app --host 127.0.0.1 --port 8000 --reload

# Run examples
python examples/local_llama_example.py

# Test endpoint
curl http://127.0.0.1:8000/health
```

## 🎯 API Usage

### Python (requests)
```python
import requests

response = requests.post(
	'http://127.0.0.1:8000/v1/chat/completions',
	json={
		'model': 'llama-local',
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
	model="llama-local",
	messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

### cURL
```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
	"model": "llama-local",
	"messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## 🗂️ Model Registry Example

```json
{
  "llama-local": {
	"type": "chat",
	"backend": "llama-cli",
	"path": "C:/Users/tsmit/models/llama-3.2-3b-instruct.Q4_K_M.gguf",
	"context_length": 8192,
	"owned_by": "local"
  }
}
```

## 📍 File Locations

```
realai/
├── realai.toml                    # Server configuration
├── realai/
│   ├── models/
│   │   ├── registry.json          # Model registry (EDIT THIS)
│   │   └── registry.json.example  # Example registry
│   └── server/
│       ├── app.py                 # Server entrypoint
│       ├── backends.py            # Backend resolver
│       └── llama_cli_backend.py   # NEW: llama-cli backend
├── docs/
│   ├── local-llama-setup.md       # Complete setup guide
│   └── LOCAL_LLAMA_README.md      # Overview & benefits
├── scripts/
│   └── setup_local_llama.py       # Setup checker tool
└── examples/
	└── local_llama_example.py     # Usage examples
```

## 🔍 Troubleshooting Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| "llama-cli not found" | Add to PATH or set in `realai.toml` |
| "Model file not found" | Check path in `registry.json` |
| Slow inference | Use Q4_K_M quantization, enable GPU |
| Out of memory | Use smaller model or Q3_K_M quantization |
| Server won't start | Check `python scripts/setup_local_llama.py` |

## 📚 Documentation

- **Complete Setup**: `docs/local-llama-setup.md`
- **Overview**: `docs/LOCAL_LLAMA_README.md`
- **Setup Checker**: `python scripts/setup_local_llama.py`
- **Examples**: `examples/local_llama_example.py`

## 🎨 Recommended Models

| Model | Size | Use Case | Download |
|-------|------|----------|----------|
| Llama 3.2 3B (Q4_K_M) | ~2GB | Fast responses | [Link](https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF) |
| Llama 3.1 7B (Q4_K_M) | ~4GB | Quality responses | [Link](https://huggingface.co/bartowski/Meta-Llama-3.1-7B-Instruct-GGUF) |
| Mistral 7B (Q4_K_M) | ~4GB | Instruction following | [Link](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF) |
| DeepSeek Coder 6.7B | ~4GB | Code generation | [Link](https://huggingface.co/TheBloke/deepseek-coder-6.7B-instruct-GGUF) |

## 🎯 Success Checklist

- [ ] llama-cli.exe downloaded and in PATH
- [ ] GGUF model downloaded to `C:\Users\tsmit\models\`
- [ ] `realai/models/registry.json` configured with model path
- [ ] Server starts without errors
- [ ] `/health` endpoint returns `"status": "ok"`
- [ ] Chat completion request returns response
- [ ] No cloud API keys required ✨

## 🔗 Quick Links

- **llama.cpp releases**: https://github.com/ggerganov/llama.cpp/releases
- **GGUF models**: https://huggingface.co/models?search=gguf
- **RealAI GitHub**: https://github.com/Unwrenchable/realai

---

**Need help?** Run `python scripts/setup_local_llama.py` to diagnose issues.
