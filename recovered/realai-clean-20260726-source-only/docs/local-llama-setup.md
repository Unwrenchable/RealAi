# Local Llama.cpp Integration Guide

This guide explains how to run RealAI completely locally using llama.cpp GGUF models, without requiring cloud API keys.

## Overview

The RealAI local inference server supports three backend modes for running GGUF models:

1. **llama-cli** (recommended): Calls `llama-cli.exe` directly via subprocess
2. **llama.cpp**: Uses llama-cpp-python bindings (requires compilation)
3. **vLLM**: GPU-accelerated inference (requires CUDA)

This guide focuses on the **llama-cli** backend, which is the easiest to set up.

---

## Prerequisites

### 1. Install llama.cpp

Download or build llama.cpp from: https://github.com/ggerganov/llama.cpp

**Option A: Pre-built Windows Release** (Easiest)
1. Download the latest Windows release from GitHub releases
2. Extract to `C:\llama.cpp` or your preferred location
3. Add the binary directory to your PATH, or configure the path in RealAI

**Option B: Build from Source**
```powershell
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
```

The `llama-cli.exe` executable will be in `build/bin/Release/`.

### 2. Download GGUF Models

Download quantized GGUF models from Hugging Face:

**Popular Models:**
- [Llama 3.2 3B Instruct](https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF)
- [Llama 3.1 7B Instruct](https://huggingface.co/bartowski/Meta-Llama-3.1-7B-Instruct-GGUF)
- [Mistral 7B Instruct](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF)

**Recommended quantization:** Q4_K_M (good balance of speed and quality)

Save models to a location like:
```
C:\Users\tsmit\models\
  ├── llama-3.2-3b-instruct.Q4_K_M.gguf
  └── llama-3.1-7b-instruct.Q4_K_M.gguf
```

---

## Configuration

### 1. Configure Model Registry

Edit `realai/models/registry.json` to add your local models:

```json
{
  "llama-local": {
	"type": "chat",
	"backend": "llama-cli",
	"path": "C:/Users/tsmit/models/llama-3.2-3b-instruct.Q4_K_M.gguf",
	"context_length": 8192,
	"owned_by": "local",
	"capabilities": ["chat", "completion"]
  }
}
```

**Configuration Fields:**
- `type`: Model type (`chat`, `completion`, or `embedding`)
- `backend`: Inference backend (`llama-cli`, `llama.cpp`, or `vllm`)
- `path`: Absolute path to GGUF model file
- `context_length`: Model's context window size
- `owned_by`: Model provider (informational)
- `capabilities`: List of supported features

### 2. Configure llama-cli Path (Optional)

If `llama-cli.exe` is not in your PATH, configure its location in `realai.toml`:

```toml
[server]
profile = "default"
provider = "local"
default_chat_model = "llama-local"

[backends.llama-cli]
llama_cli_path = "C:/llama.cpp/build/bin/Release/llama-cli.exe"
```

---

## Running the Server

### Start RealAI Server

```powershell
# Navigate to your RealAI directory
cd C:\Users\tsmit\source\repos\Unwrenchable\realai

# Start the server (defaults to http://127.0.0.1:8000)
python -m realai.server.app

# Or with uvicorn (FastAPI mode):
uvicorn realai.server.app:app --host 127.0.0.1 --port 8000
```

### Verify Server Health

```powershell
curl http://127.0.0.1:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "provider": "local",
  "profile": "default",
  "available_models": ["llama-local", "llama-local-7b", ...]
}
```

---

## Using the Local Server

### From Python

```python
import requests

response = requests.post(
	'http://127.0.0.1:8000/v1/chat/completions',
	json={
		'model': 'llama-local',
		'messages': [
			{'role': 'user', 'content': 'What is the capital of France?'}
		],
		'temperature': 0.7,
		'max_tokens': 512
	}
)

print(response.json()['choices'][0]['message']['content'])
```

### From RealAI CLI

If you have a RealAI CLI configured to use the local endpoint:

```powershell
# Configure RealAI to use local server
$env:REALAI_API_BASE = "http://127.0.0.1:8000/v1"
$env:REALAI_API_KEY = "local"  # Any value works for local server

# Run chat
realai chat --model llama-local "What is 2+2?"
```

### From OpenAI-Compatible Clients

Any OpenAI-compatible client can use your local server:

```python
from openai import OpenAI

client = OpenAI(
	base_url="http://127.0.0.1:8000/v1",
	api_key="local"  # Any value works
)

response = client.chat.completions.create(
	model="llama-local",
	messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

---

## Advanced Configuration

### GPU Acceleration

To enable GPU acceleration with llama-cli, llama.cpp must be built with CUDA support:

```powershell
# Build with CUDA
cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_CUBLAS=ON
cmake --build build --config Release
```

Then models will automatically use GPU layers when available.

### Performance Tuning

Add sampling parameters to your model config:

```json
{
  "llama-local": {
	"type": "chat",
	"backend": "llama-cli",
	"path": "C:/Users/tsmit/models/llama-3.2-3b-instruct.Q4_K_M.gguf",
	"context_length": 8192,
	"top_p": 0.95,
	"temperature": 0.7,
	"repetition_penalty": 1.1
  }
}
```

### Multiple Models

Configure multiple models for different use cases:

```json
{
  "llama-fast": {
	"backend": "llama-cli",
	"path": "C:/Users/tsmit/models/llama-3.2-3b-instruct.Q4_K_M.gguf",
	"context_length": 8192
  },
  "llama-quality": {
	"backend": "llama-cli",
	"path": "C:/Users/tsmit/models/llama-3.1-7b-instruct.Q4_K_M.gguf",
	"context_length": 32768
  }
}
```

---

## Troubleshooting

### Server Won't Start

**Error:** `llama-cli backend not available`

**Solution:** Verify llama-cli.exe is in your PATH or configure the path:
```powershell
where llama-cli
# or
$env:PATH += ";C:\llama.cpp\build\bin\Release"
```

### Model Not Loading

**Error:** `Model file not found: C:/Users/tsmit/models/...`

**Solution:** Check the path in `registry.json` and verify the file exists:
```powershell
Test-Path "C:\Users\tsmit\models\llama-3.2-3b-instruct.Q4_K_M.gguf"
```

### Slow Inference

**Issue:** Generation takes longer than expected

**Solutions:**
1. Use a smaller quantization (Q4_K_M instead of Q8_0)
2. Enable GPU acceleration (rebuild llama.cpp with CUDA)
3. Reduce `max_tokens` in requests
4. Use a smaller model (3B instead of 7B)

### Out of Memory

**Error:** `llama-cli process killed` or system freezes

**Solutions:**
1. Use a more aggressive quantization (Q3_K_M or Q2_K)
2. Use a smaller model
3. Reduce context length in model config
4. Add swap space (Windows page file)

---

## API Endpoints

The RealAI local server implements OpenAI-compatible endpoints:

### Chat Completions
```
POST /v1/chat/completions
```

### Text Completions
```
POST /v1/completions
```

### List Models
```
GET /v1/models
```

### Model Details
```
GET /v1/models/{model_id}
```

### Health Check
```
GET /health
```

### Metrics (Prometheus)
```
GET /metrics
```

---

## Architecture

```
┌─────────────────┐
│  RealAI CLI     │
│  or Client      │
└────────┬────────┘
		 │ HTTP
		 ▼
┌─────────────────┐
│  FastAPI Server │
│  (app.py)       │
└────────┬────────┘
		 │
		 ▼
┌─────────────────┐
│ Backend Resolver│
│  (backends.py)  │
└────────┬────────┘
		 │
	┌────┼────┬──────────┐
	▼    ▼    ▼          ▼
 ┌────┐ ┌──┐ ┌────────┐ ┌────────┐
 │vLLM│ │cpp│ │llama-cli│ │fallback│
 └────┘ └──┘ └────┬───┘ └────────┘
				   │
				   ▼ subprocess
		   ┌──────────────┐
		   │ llama-cli.exe│
		   └──────┬───────┘
				  │
				  ▼
		   ┌──────────────┐
		   │  GGUF Model  │
		   └──────────────┘
```

---

## Next Steps

1. ✅ **Basic Setup Complete** - You can now run RealAI locally!
2. 🔄 **Add Streaming** - Implement streaming responses for real-time output
3. 🎯 **Add Embeddings** - Implement `/v1/embeddings` endpoint for semantic search
4. 🔍 **Add Reranking** - Implement reranking models for RAG pipelines
5. 🚀 **Multi-Model Routing** - Route requests to different models based on complexity
6. 📊 **Monitoring** - Set up Prometheus metrics and dashboards

---

## Success Criteria

- ✅ RealAI successfully sends requests to local server
- ✅ Local server calls llama-cli.exe and returns model output
- ✅ RealAI displays responses from local model instead of placeholder
- ✅ Fully local AI stack with no cloud API dependencies

**Congratulations!** You've achieved a complete local AI infrastructure.
