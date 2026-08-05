# 🏠 Running RealAI Locally with Llama.cpp

This section is an addition to the main README, providing specific instructions for running RealAI with local llama.cpp GGUF models.

## Overview

RealAI now supports three local inference backends:

1. **🔧 llama-cli** (NEW!) - Calls llama-cli.exe directly (easiest, no compilation)
2. **🐍 llama-cpp-python** - Python bindings to llama.cpp (requires compilation)
3. **⚡ vLLM** - GPU-accelerated inference (requires CUDA)

The **llama-cli** backend is the recommended approach for most users because:
- ✅ No Python compilation required
- ✅ Works with pre-built llama.cpp binaries
- ✅ Easy to update (just replace the binary)
- ✅ Supports CPU and GPU acceleration
- ✅ Compatible with all GGUF models

## Quick Start (5 Minutes)

### 1. Install llama.cpp

**Download pre-built binary** (Windows):
```powershell
# Download from: https://github.com/ggerganov/llama.cpp/releases
# Extract to C:\llama.cpp\ or your preferred location
# Add to PATH or configure path in RealAI
```

**Or build from source:**
```powershell
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
```

### 2. Download a GGUF Model

Download a quantized GGUF model from Hugging Face:

**Recommended models:**
- [Llama 3.2 3B Instruct](https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF) - Fast, good quality (Q4_K_M)
- [Llama 3.1 7B Instruct](https://huggingface.co/bartowski/Meta-Llama-3.1-7B-Instruct-GGUF) - Higher quality (Q4_K_M)
- [Mistral 7B Instruct](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF) - Fast 7B model (Q4_K_M)

Save to: `C:\Users\tsmit\models\`

### 3. Configure RealAI

Edit `realai/models/registry.json` to add your model:

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

### 4. Start the Server

```powershell
cd C:\Users\tsmit\source\repos\Unwrenchable\realai

# Option 1: Basic server
python -m realai.server.app

# Option 2: FastAPI with auto-reload (recommended for development)
uvicorn realai.server.app:app --host 127.0.0.1 --port 8000 --reload
```

### 5. Test It!

```python
import requests

response = requests.post(
	'http://127.0.0.1:8000/v1/chat/completions',
	json={
		'model': 'llama-local',
		'messages': [
			{'role': 'user', 'content': 'What is 2+2?'}
		]
	}
)

print(response.json()['choices'][0]['message']['content'])
```

**OR** run the example script:

```powershell
python examples/local_llama_example.py
```

## Setup Verification

Run the setup checker to verify your configuration:

```powershell
python scripts/setup_local_llama.py
```

This will check:
- ✅ llama-cli is available
- ✅ GGUF models are present
- ✅ Model registry is configured
- ✅ Python dependencies are installed
- ✅ Server can start successfully

## Benefits of Local Inference

### 🔒 Privacy
Your data never leaves your machine. Perfect for:
- Sensitive business data
- Personal information
- Proprietary code
- Medical/legal documents

### 💰 Cost Savings
No per-token API charges:
- GPT-4: $0.03 per 1K tokens
- RealAI Local: **$0.00** ✨

**Example savings:**
- 1M tokens/month with GPT-4: **$30/month**
- 1M tokens/month with RealAI Local: **$0/month**
- **Annual savings: $360**

### 🚀 Performance
No network latency, no rate limits:
- API calls: ~500-2000ms latency
- Local inference: **0ms network latency**
- Rate limits: None
- Concurrent requests: Limited only by your hardware

### 🌐 Offline Capability
Works without internet:
- Travel
- Remote locations
- Network outages
- Air-gapped environments

## Advanced Features

### GPU Acceleration

Enable GPU for 10-50x speedup:

```powershell
# Rebuild llama.cpp with CUDA
cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_CUBLAS=ON
cmake --build build --config Release
```

Models will automatically use GPU when available.

### Multiple Models

Configure different models for different use cases:

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
  },
  "llama-code": {
	"backend": "llama-cli",
	"path": "C:/Users/tsmit/models/deepseek-coder-6.7b.Q4_K_M.gguf",
	"context_length": 16384
  }
}
```

Then route requests based on task:
```python
# Fast responses
response = client.chat.create(model='llama-fast', ...)

# High quality reasoning
response = client.chat.create(model='llama-quality', ...)

# Code generation
response = client.chat.create(model='llama-code', ...)
```

### Custom Sampling

Configure per-model generation parameters:

```json
{
  "llama-creative": {
	"backend": "llama-cli",
	"path": "C:/Users/tsmit/models/llama-3.1-7b-instruct.Q4_K_M.gguf",
	"temperature": 0.9,
	"top_p": 0.95,
	"repetition_penalty": 1.1
  }
}
```

## Architecture

```
┌──────────────────┐
│   Client Code    │
└────────┬─────────┘
		 │ HTTP
		 ▼
┌──────────────────┐
│  RealAI Server   │
│   (FastAPI)      │
└────────┬─────────┘
		 │
		 ▼
┌──────────────────┐
│Backend Resolver  │
└────────┬─────────┘
		 │
	┌────┼────┬──────────┐
	▼    ▼    ▼          ▼
 ┌────┐ ┌──┐ ┌────────┐ ┌────┐
 │vLLM│ │cpp│ │llama-cli│ │fall│
 └────┘ └──┘ └────┬───┘ └────┘
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

## Performance Comparison

| Backend | Speed (tok/s) | Setup | GPU | Memory |
|---------|--------------|-------|-----|--------|
| vLLM | 100-500 | Hard | Required | High |
| llama.cpp | 20-100 | Medium | Optional | Medium |
| **llama-cli** | **20-100** | **Easy** | **Optional** | **Medium** |

**Typical speeds (Q4_K_M, CPU):**
- 3B model: ~20-30 tokens/sec
- 7B model: ~8-15 tokens/sec
- 13B model: ~4-8 tokens/sec

**With GPU (CUDA):**
- 3B model: ~80-120 tokens/sec
- 7B model: ~40-80 tokens/sec
- 13B model: ~20-40 tokens/sec

## Troubleshooting

### "llama-cli not found"

**Solution:** Add llama-cli to PATH or configure path in `realai.toml`:

```toml
[backends.llama-cli]
llama_cli_path = "C:/llama.cpp/build/bin/Release/llama-cli.exe"
```

### "Model file not found"

**Solution:** Verify the path in `registry.json` matches your model location:

```powershell
Test-Path "C:\Users\tsmit\models\llama-3.2-3b-instruct.Q4_K_M.gguf"
```

### Slow inference

**Solutions:**
1. Use smaller quantization (Q4_K_M instead of Q8_0)
2. Enable GPU acceleration
3. Use smaller model (3B instead of 7B)
4. Reduce `max_tokens` in requests

### Out of memory

**Solutions:**
1. Use more aggressive quantization (Q3_K_M or Q2_K)
2. Use smaller model
3. Reduce context length
4. Add more RAM/swap

## Complete Documentation

📖 **[Full Setup Guide](docs/local-llama-setup.md)** - Complete documentation with advanced features

📝 **[Example Scripts](examples/local_llama_example.py)** - Working code examples

🔧 **[Setup Checker](scripts/setup_local_llama.py)** - Verify your installation

## API Compatibility

The RealAI local server implements OpenAI-compatible endpoints:

- `POST /v1/chat/completions` - Chat completions
- `POST /v1/completions` - Text completions
- `GET /v1/models` - List available models
- `GET /v1/models/{model_id}` - Model details
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

Any OpenAI-compatible client can use your local RealAI server by setting:
```python
base_url = "http://127.0.0.1:8000/v1"
api_key = "local"  # Any value works
```

## Success Criteria

After setup, you should have:
- ✅ RealAI server running on http://127.0.0.1:8000
- ✅ Local GGUF models configured in registry
- ✅ llama-cli backend available and working
- ✅ Chat completions returning responses from local models
- ✅ Zero dependency on cloud APIs
- ✅ Fully local AI infrastructure

**🎉 Congratulations! You now have a complete local AI stack.**

## Next Steps

1. **Try different models** - Experiment with various GGUF models
2. **Enable GPU** - Rebuild llama.cpp with CUDA for massive speedup
3. **Add embeddings** - Configure local embedding models for RAG
4. **Implement streaming** - Add streaming responses for real-time output
5. **Build agents** - Create specialized AI agents using local models

---

**Need help?** See the [full documentation](docs/local-llama-setup.md) or run the [setup checker](scripts/setup_local_llama.py).
