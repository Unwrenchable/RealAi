# RealAI Local Inference - Final Setup Guide

## ✅ Status: WORKING

Your local llama.cpp model is now running and ready to be used by RealAI!

## What's Running

- **Backend**: llama.cpp native server (`llama-server.exe`)
- **Model**: Llama 3.2 1B Instruct (Q4_K_M quantization)
- **Location**: `C:\Users\tsmit\OneDrive\Apps\realai\models\llama3.2-1b\Llama-3.2-1B-Instruct-Q4_K_M.gguf`
- **Endpoint**: http://127.0.0.1:8080/v1
- **Compatible**: OpenAI API format (chat completions, completions)

## How to Start the Server

### Option 1: Using the batch file (easiest)
```batch
start_realai_server.bat
```

### Option 2: Manual command
```powershell
C:\llama.cpp\build\bin\Release\llama-server.exe `
  -m "C:\Users\tsmit\OneDrive\Apps\realai\models\llama3.2-1b\Llama-3.2-1B-Instruct-Q4_K_M.gguf" `
  --host 127.0.0.1 `
  --port 8080 `
  -c 4096
```

## Configure RealAI

Once the server is running, configure your RealAI CLI or application:

```bash
# For RealAI CLI (if supported)
realai config set api_base_url http://127.0.0.1:8080/v1
realai config set api_key local
```

Or in your RealAI configuration file:
```yaml
providers:
  - type: openai
	name: local-llama
	base_url: http://127.0.0.1:8080/v1
	api_key: local  # Can be any value

default_provider: local-llama
```

## Test the Server

### Using PowerShell
```powershell
$body = @{
	model = 'llama-3.2-1b'
	messages = @(@{
		role = 'user'
		content = 'Hello! Who are you?'
	})
	max_tokens = 100
} | ConvertTo-Json -Depth 10

$response = Invoke-RestMethod `
	-Uri 'http://127.0.0.1:8080/v1/chat/completions' `
	-Method Post `
	-Body $body `
	-ContentType 'application/json'

Write-Host $response.choices[0].message.content
```

### Using Python
```python
import requests

response = requests.post(
	'http://127.0.0.1:8080/v1/chat/completions',
	json={
		'model': 'llama-3.2-1b',
		'messages': [
			{'role': 'user', 'content': 'Hello! Who are you?'}
		],
		'max_tokens': 100
	}
)

print(response.json()['choices'][0]['message']['content'])
```

### Using curl
```bash
curl -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
	"model": "llama-3.2-1b",
	"messages": [{"role": "user", "content": "Hello!"}],
	"max_tokens": 50
  }'
```

## Available Endpoints

The llama-server exposes a full OpenAI-compatible API:

- `GET /health` - Health check
- `GET /v1/models` - List available models
- `POST /v1/chat/completions` - Chat completions
- `POST /v1/completions` - Text completions
- `POST /v1/embeddings` - Text embeddings

## Web UI

llama-server also includes a built-in web UI! Open your browser to:

```
http://127.0.0.1:8080
```

You'll see a chat interface where you can interact with your model directly.

## Performance

Your current setup:
- **Model size**: ~807 MB (quantized)
- **Context window**: 4096 tokens
- **Speed**: ~38 tokens/second (generation)
- **Backend**: CPU inference

## Next Steps

### 1. Configure RealAI
Point RealAI at your local server using the config above.

### 2. Add More Models
Download additional GGUF models:
```powershell
# Example: Download Llama 3.1 8B
Invoke-WebRequest `
  -Uri "https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct-GGUF/resolve/main/Llama-3.1-8B-Instruct-Q4_K_M.gguf" `
  -OutFile "C:\Users\tsmit\OneDrive\Apps\realai\models\llama3.1-8b\model.gguf"
```

Then start the server with the new model path.

### 3. GPU Acceleration (Optional)
If you have an NVIDIA GPU, rebuild llama.cpp with CUDA support for 10-50x faster inference.

### 4. Deploy to Server
When ready, deploy this same setup to Vercel/Render by:
- Containerizing llama-server
- Mounting your model files
- Exposing port 8080

## Troubleshooting

### Server won't start
- Check if port 8080 is already in use: `netstat -ano | findstr :8080`
- Verify model file exists: `Test-Path "C:\Users\tsmit\OneDrive\Apps\realai\models\llama3.2-1b\Llama-3.2-1B-Instruct-Q4_K_M.gguf"`

### Slow inference
- Reduce context size: `-c 2048` instead of `-c 4096`
- Use smaller model: Try a 1B or 3B model instead of 7B+
- Enable GPU: Rebuild with CUDA support

### RealAI not connecting
- Verify server is running: `curl http://127.0.0.1:8080/health`
- Check RealAI config points to correct base URL: `http://127.0.0.1:8080/v1`
- API key can be any value (not validated for local server)

## Files Created

- `start_realai_server.bat` - Easy launcher for the server
- `realai_local_server.py` - Custom FastAPI wrapper (not needed with native llama-server)
- `test_local_server.py` - Test script

## What We Built

1. ✅ Built llama.cpp from source
2. ✅ Located and configured the correct model
3. ✅ Set up llama-server with OpenAI-compatible API
4. ✅ Verified chat completions work
5. ✅ Created easy-launch scripts
6. ✅ Ready for RealAI integration

---

**You're done!** 🎉

Your local LLaMA model is running, tested, and ready to power RealAI with zero cloud dependencies.
