# 🔄 Migration Guide: Switching to Local Llama.cpp

This guide helps you migrate from cloud-based RealAI to fully local inference using llama.cpp.

## Why Migrate?

### Before (Cloud API)
- ❌ Requires API keys (OpenAI, Anthropic, etc.)
- ❌ Per-token costs (~$30/month for 1M tokens)
- ❌ Rate limits and quotas
- ❌ Data sent to external servers
- ❌ Requires internet connection

### After (Local Llama.cpp)
- ✅ No API keys required
- ✅ Zero per-token costs
- ✅ No rate limits
- ✅ Data stays on your machine
- ✅ Works offline

## Migration Path

### Step 1: Check Your Current Setup

Run this to see your current configuration:

```powershell
# Check current RealAI configuration
$env:REALAI_API_KEY
$env:REALAI_API_BASE
```

If you have API keys configured, you can keep them as fallbacks or remove them entirely.

### Step 2: Install llama.cpp

**Option A: Download Pre-built Binary (Easiest)**

```powershell
# 1. Download from GitHub releases
# Visit: https://github.com/ggerganov/llama.cpp/releases
# Download: llama-cli-win-x64.zip (or similar)

# 2. Extract to a permanent location
Expand-Archive -Path llama-cli-win-x64.zip -DestinationPath C:\llama.cpp

# 3. Add to PATH (optional but recommended)
$env:PATH += ";C:\llama.cpp"

# 4. Verify installation
llama-cli --version
```

**Option B: Build from Source (Advanced)**

```powershell
# Requires: CMake, Visual Studio Build Tools
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release

# Binary will be in: build/bin/Release/llama-cli.exe
```

### Step 3: Download GGUF Models

Choose models based on your hardware:

**For 8GB RAM (Minimum)**
- Llama 3.2 3B (Q4_K_M) - ~2GB
- Download: https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF

**For 16GB RAM (Recommended)**
- Llama 3.1 7B (Q4_K_M) - ~4GB
- Download: https://huggingface.co/bartowski/Meta-Llama-3.1-7B-Instruct-GGUF

**For 32GB+ RAM (High Quality)**
- Llama 3.1 13B (Q4_K_M) - ~8GB
- Mistral 7B (Q5_K_M) - ~5GB

**Create models directory:**
```powershell
mkdir C:\Users\$env:USERNAME\models
# Download GGUF files to this directory
```

### Step 4: Update RealAI Configuration

**Edit `realai/models/registry.json`:**

```json
{
  "// Comment": "Your existing cloud models can stay here as fallbacks",

  "// NEW: Local models (use these by default)": "",
  "llama-local": {
	"type": "chat",
	"backend": "llama-cli",
	"path": "C:/Users/YOUR_USERNAME/models/llama-3.2-3b-instruct.Q4_K_M.gguf",
	"context_length": 8192,
	"owned_by": "local"
  },

  "// EXISTING: Cloud models (keep as fallbacks)": "",
  "gpt-4": {
	"type": "chat",
	"backend": "openai",
	"path": "gpt-4",
	"context_length": 8192
  }
}
```

**Create/Edit `realai.toml`:**

```toml
[server]
# Use local model by default
default_chat_model = "llama-local"

# Optionally specify llama-cli path if not in PATH
[backends.llama-cli]
# llama_cli_path = "C:/llama.cpp/llama-cli.exe"
```

### Step 5: Start Local Server

```powershell
# Navigate to RealAI directory
cd C:\Users\$env:USERNAME\source\repos\Unwrenchable\realai

# Start server
python -m realai.server.app

# Or with auto-reload (for development)
uvicorn realai.server.app:app --reload
```

Expected output:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 6: Update Client Configuration

**Python SDK:**

```python
from realai import RealAIClient

# OLD: Cloud API
# client = RealAIClient(api_key="sk-...")

# NEW: Local server
client = RealAIClient(
	base_url="http://127.0.0.1:8000/v1",
	api_key="local"  # Any value works for local
)

# Use as normal
response = client.chat.create(
	model="llama-local",  # Use your local model
	messages=[{"role": "user", "content": "Hello!"}]
)
```

**Environment Variables:**

```powershell
# OLD: Cloud API
# $env:OPENAI_API_KEY = "sk-..."
# $env:REALAI_API_BASE = "https://api.openai.com/v1"

# NEW: Local server
$env:REALAI_API_BASE = "http://127.0.0.1:8000/v1"
$env:REALAI_API_KEY = "local"

# Or set permanently
[System.Environment]::SetEnvironmentVariable('REALAI_API_BASE', 'http://127.0.0.1:8000/v1', 'User')
[System.Environment]::SetEnvironmentVariable('REALAI_API_KEY', 'local', 'User')
```

**RealAI CLI:**

```powershell
# OLD: Configure cloud API
# realai config set api_key sk-...

# NEW: Configure local server
realai config set api_base http://127.0.0.1:8000/v1
realai config set api_key local

# Test
realai chat "Hello, how are you?" --model llama-local
```

### Step 7: Verify Migration

Run the setup checker:

```powershell
python scripts/setup_local_llama.py
```

Expected output:
```
✅ llama-cli available: True
✅ GGUF models found: 1
✅ Registry configured: True
✅ Dependencies installed: True
✅ Server ready: True

🎉 All checks passed! You're ready to run RealAI locally.
```

### Step 8: Test End-to-End

```python
import requests

# Test health
health = requests.get('http://127.0.0.1:8000/health').json()
print(f"Provider: {health['provider']}")
print(f"Models: {health['available_models']}")

# Test chat
response = requests.post(
	'http://127.0.0.1:8000/v1/chat/completions',
	json={
		'model': 'llama-local',
		'messages': [{'role': 'user', 'content': 'What is 2+2?'}]
	}
).json()

print(f"Response: {response['choices'][0]['message']['content']}")
print(f"Backend used: {response.get('backend')}")
```

Expected output:
```
Provider: local
Models: ['llama-local', ...]
Response: 2+2 equals 4.
Backend used: llama-cli
```

## Migration Strategies

### Strategy 1: Full Migration (Recommended)

**Use Case**: You want to go fully local, no cloud dependencies

1. Install llama.cpp and download models
2. Configure local models as default
3. Remove cloud API keys (optional)
4. Point all clients to local server

**Pros**: Maximum privacy, zero costs, no external dependencies  
**Cons**: Limited to local hardware capacity

### Strategy 2: Hybrid Setup

**Use Case**: Use local for most tasks, cloud for complex/specialized tasks

1. Install llama.cpp and configure local models
2. Keep cloud API keys configured
3. Use local models by default
4. Switch to cloud models for specific use cases

```python
# Local for routine tasks
response = client.chat.create(
	model="llama-local",
	messages=[...]
)

# Cloud for complex reasoning
response = client.chat.create(
	model="gpt-4",  # Falls back to cloud
	messages=[...]
)
```

**Pros**: Flexibility, best of both worlds  
**Cons**: Still need API keys, some data goes to cloud

### Strategy 3: Gradual Migration

**Use Case**: Test local setup before fully committing

**Phase 1: Testing (Week 1-2)**
1. Install llama.cpp
2. Configure one local model
3. Test with non-critical workloads
4. Keep cloud as primary

**Phase 2: Partial Migration (Week 3-4)**
1. Use local for development/testing
2. Use cloud for production
3. Compare quality and performance

**Phase 3: Full Migration (Week 5+)**
1. Switch default to local
2. Use cloud only for edge cases
3. Eventually remove cloud API keys

## Troubleshooting Migration Issues

### Issue: Server won't start

**Error**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**:
```powershell
pip install fastapi uvicorn
```

### Issue: "llama-cli not found"

**Solution**:
```powershell
# Option 1: Add to PATH
$env:PATH += ";C:\path\to\llama.cpp"

# Option 2: Configure in realai.toml
# [backends.llama-cli]
# llama_cli_path = "C:/path/to/llama-cli.exe"

# Option 3: Copy to system directory
copy C:\path\to\llama-cli.exe C:\Windows\System32\
```

### Issue: Clients can't connect to server

**Error**: `Connection refused` or `Connection timeout`

**Solutions**:
1. Verify server is running: `curl http://127.0.0.1:8000/health`
2. Check firewall isn't blocking port 8000
3. Verify `REALAI_API_BASE` is set correctly

### Issue: Local model quality is poor

**Solutions**:
1. Try a larger model (7B instead of 3B)
2. Use better quantization (Q5_K_M instead of Q4_K_M)
3. Adjust temperature/sampling parameters
4. Use model specialized for your task (e.g., DeepSeek for code)

### Issue: Local inference is slow

**Solutions**:
1. Enable GPU acceleration (rebuild llama.cpp with CUDA)
2. Use more aggressive quantization (Q4_K_M instead of Q6_K)
3. Use smaller model (3B instead of 7B)
4. Reduce `max_tokens` in requests
5. Upgrade hardware (more RAM, better CPU/GPU)

## Rollback Plan

If you need to revert to cloud APIs:

```powershell
# 1. Restore API keys
$env:OPENAI_API_KEY = "sk-your-key"
$env:REALAI_API_BASE = "https://api.openai.com/v1"

# 2. Update default model in realai.toml
# default_chat_model = "gpt-3.5-turbo"

# 3. Restart clients
# No server restart needed if using cloud APIs directly
```

## Cost Comparison

### Before Migration (Cloud API)
```
GPT-3.5 Turbo: $0.002 per 1K tokens
GPT-4: $0.03 per 1K tokens

Monthly usage: 1M tokens
Cost: $20-30/month
Annual: $240-360
```

### After Migration (Local)
```
Initial Setup: 
- llama.cpp: Free
- GGUF models: Free
- Electricity: ~$1-5/month (varies)

Monthly cost: ~$1-5
Annual: ~$12-60

Savings: $228-348/year (95%+ reduction)
```

## Performance Comparison

| Metric | Cloud API | Local (CPU) | Local (GPU) |
|--------|-----------|-------------|-------------|
| Latency | 500-2000ms | 100-500ms | 50-200ms |
| Network | Yes | No | No |
| Cost | Per-token | Electricity | Electricity |
| Privacy | Low | High | High |
| Rate Limit | Yes | No | No |
| Offline | No | Yes | Yes |
| Speed | Fast | 20-30 tok/s | 80-500 tok/s |

## Success Checklist

- [ ] llama-cli.exe installed and accessible
- [ ] GGUF model(s) downloaded
- [ ] `realai/models/registry.json` configured
- [ ] Local server starts without errors
- [ ] Health endpoint returns 200 OK
- [ ] Chat completion returns valid response
- [ ] Client code updated to use local server
- [ ] Environment variables updated
- [ ] Setup checker passes all tests
- [ ] Example scripts work correctly
- [ ] Backup plan documented (if needed)

## Next Steps After Migration

1. **Optimize Performance**
   - Enable GPU acceleration
   - Try different quantization levels
   - Tune sampling parameters

2. **Add More Models**
   - Code generation (DeepSeek Coder)
   - Instruction following (Mistral)
   - Chat (Llama 3.1 7B)

3. **Advanced Features**
   - Set up embeddings for RAG
   - Configure reranking models
   - Implement streaming responses

4. **Production Deployment**
   - Run server as Windows service
   - Set up monitoring and logging
   - Configure automatic restarts
   - Add authentication if exposing externally

## Support Resources

- **Documentation**: `docs/local-llama-setup.md`
- **Quick Reference**: `QUICKSTART_LOCAL.md`
- **Setup Checker**: `python scripts/setup_local_llama.py`
- **Examples**: `examples/local_llama_example.py`
- **llama.cpp GitHub**: https://github.com/ggerganov/llama.cpp
- **GGUF Models**: https://huggingface.co/models?search=gguf

---

**Questions or issues?** Run `python scripts/setup_local_llama.py` for automated diagnostics.
