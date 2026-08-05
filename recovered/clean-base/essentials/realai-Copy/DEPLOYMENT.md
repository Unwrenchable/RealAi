# RealAI Deployment Guide

This guide covers all deployment options for RealAI, from local development to production cloud deployments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Desktop Application (Windows .exe)](#desktop-application-windows-exe)
4. [API Server Deployment](#api-server-deployment)
   - [Local/Development Server](#localdevelopment-server)
   - [Production Server](#production-server)
5. [AWS Lambda Deployment](#aws-lambda-deployment)
6. [Environment Variables](#environment-variables)
7. [Testing Your Deployment](#testing-your-deployment)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required
- **Python 3.7+** (Python 3.11 recommended for Lambda)
- **pip** package manager

### For AWS Lambda Deployment
- **AWS Account** with appropriate permissions
- **AWS CLI** configured with credentials
- **AWS SAM CLI** for serverless deployment

### For Windows .exe Build
- **PyInstaller** (`pip install pyinstaller`)
- **tkinter** (included with Python from python.org)

---

## Local Development

Perfect for development, testing, or personal use.

### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/Unwrenchable/realai.git
cd realai

# Install in editable mode
pip install -e .
```

### 2. Set Up API Keys

You need at least one AI provider API key. Choose one or more:

```bash
# OpenAI (recommended for getting started)
export REALAI_OPENAI_API_KEY=sk-...

# Anthropic Claude
export REALAI_ANTHROPIC_API_KEY=sk-ant-...

# xAI / Grok
export REALAI_GROK_API_KEY=xai-...

# Google Gemini
export REALAI_GEMINI_API_KEY=AIza...

# OpenRouter (access to 200+ models with one key)
export REALAI_OPENROUTER_API_KEY=sk-or-v1-...

# Mistral AI
export REALAI_MISTRAL_API_KEY=...

# Together AI
export REALAI_TOGETHER_API_KEY=...

# DeepSeek
export REALAI_DEEPSEEK_API_KEY=...

# Perplexity AI
export REALAI_PERPLEXITY_API_KEY=pplx-...
```

**Windows users:** Use `set` instead of `export`:
```cmd
set REALAI_OPENAI_API_KEY=sk-...
```

### 3. Run the Examples

```bash
# Test the installation
python examples.py

# Run tests
python test_realai.py
```

### 4. Use in Your Code

```python
from realai import RealAIClient

client = RealAIClient()
response = client.chat.create(
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response['choices'][0]['message']['content'])
```

---

## Desktop Application (Windows .exe)

Build a standalone Windows executable with GUI, API server, and built-in chat.

### Run Without Building

```bash
python realai_gui.py
```

### Build Standalone .exe

```bash
# Install PyInstaller (one-time)
pip install pyinstaller

# Build the executable
pyinstaller realai_launcher.spec

# Output: dist\RealAI.exe
```

### Using the Desktop App

1. **Launch** `RealAI.exe`
2. **Configure API Keys**
   - Enter your API key(s) in the setup panel
   - Click **Save Keys** (stored locally in `~/.realai/config.json`)
3. **Start the Server**
   - Click **🚀 Start API Server**
   - Server runs at `http://localhost:8000`
4. **Use Built-in Chat**
   - Type messages in the chat panel at the bottom
   - Press Enter or click **➤ Send**

### Distribution

The `RealAI.exe` file is fully self-contained:
- ✅ No Python installation required on target machine
- ✅ Includes GUI, API server, and core RealAI module
- ✅ All dependencies bundled
- ✅ Single file distribution

---

## API Server Deployment

### Local/Development Server

Quick setup for local development or testing.

#### Option A: Using the GUI (Recommended)

1. Launch `RealAI.exe` or `python realai_gui.py`
2. Enter API key(s) and click **Save Keys**
3. Click **🚀 Start API Server**
4. Server available at `http://localhost:8000`

#### Option B: Command Line

```bash
# Set API key
export REALAI_OPENAI_API_KEY=sk-...

# Start the server (default port 8000)
python -m realai.api_server
# or (legacy, still works)
python api_server.py

# Custom port (use PORT env var)
PORT=8080 python -m realai.api_server
```

### Production Server

For deploying the API server on a VPS, cloud instance, or on-premises server.

#### 1. Install Dependencies

```bash
# Clone the repository
git clone https://github.com/Unwrenchable/realai.git
cd realai

# Install full dependencies
pip install -r requirements-full.txt
```

#### 2. Configure Environment

Create a `.env` file or set environment variables:

```bash
# Required: At least one provider API key
REALAI_OPENAI_API_KEY=sk-...
REALAI_ANTHROPIC_API_KEY=sk-ant-...

# Optional: Server configuration
API_PORT=8000
API_HOST=0.0.0.0
```

#### 3. Run with Production Server

Using **Gunicorn** (recommended for production):

```bash
# Install Gunicorn
pip install gunicorn

# Run with 4 workers
gunicorn api_server:app \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
```

Using **systemd** service (Linux):

Create `/etc/systemd/system/realai.service`:

```ini
[Unit]
Description=RealAI API Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/realai
Environment="REALAI_OPENAI_API_KEY=sk-..."
Environment="REALAI_ANTHROPIC_API_KEY=sk-ant-..."
ExecStart=/usr/bin/python3 /opt/realai/api_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable realai
sudo systemctl start realai
sudo systemctl status realai
```

#### 4. Reverse Proxy (Optional)

Using **nginx** for SSL/TLS and domain routing:

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
    }
}
```

For HTTPS, use **Certbot**:

```bash
sudo certbot --nginx -d api.yourdomain.com
```

---

## AWS Lambda Deployment

Serverless deployment using AWS Lambda with optimized, split architecture.

### Architecture Overview

RealAI uses a **split Lambda architecture** with 6 separate functions:

1. **lambda-core** - Core API endpoints (~5 MB)
   - `/health`, `/v1/models`, `/v1/capabilities`
2. **lambda-chat** - Chat and completions (~10 MB)
   - `/v1/chat/completions`, `/v1/completions`
3. **lambda-image** - Image generation (~5 MB)
   - `/v1/images/generations`
4. **lambda-video** - Video generation (~5 MB)
   - `/v1/videos/generations`
5. **lambda-embeddings-audio** - Embeddings and audio (~5 MB)
   - `/v1/embeddings`, `/v1/audio/transcriptions`, `/v1/audio/speech`
6. **lambda-advanced** - Advanced AI capabilities (~10 MB)
   - `/v1/reasoning/chain`, `/v1/synthesis/knowledge`, `/v1/reflection/analyze`, `/v1/agents/orchestrate`

All functions are **under 50 MB** (well within AWS limits).

### Prerequisites

```bash
# Install AWS CLI
pip install awscli

# Install AWS SAM CLI
pip install aws-sam-cli

# Configure AWS credentials
aws configure
```

You'll need:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., `us-east-1`)

### Deployment Steps

#### 1. Build Lambda Functions

```bash
# Build all functions
sam build

# Or build manually
./build_lambda.sh
```

#### 2. Deploy to AWS

**Guided deployment (first time):**

```bash
sam deploy --guided
```

Follow the prompts:
- **Stack name**: `realai-lambda` (or your preferred name)
- **AWS Region**: `us-east-1` (or your preferred region)
- **Confirm changes before deploy**: `Y`
- **Allow SAM CLI IAM role creation**: `Y`
- **Save arguments to configuration file**: `Y`

**Subsequent deployments:**

```bash
sam deploy
```

#### 3. Set Environment Variables

After deployment, add API keys in AWS Console:

1. Go to **Lambda** → **Functions**
2. Select each function (e.g., `realai-chat`)
3. **Configuration** → **Environment variables** → **Edit**
4. Add:
   - `REALAI_OPENAI_API_KEY`: `sk-...`
   - `REALAI_ANTHROPIC_API_KEY`: `sk-ant-...`
   - (any other provider keys you need)

Or set during deployment:

```bash
sam deploy --parameter-overrides \
  REALAI_OPENAI_API_KEY=sk-... \
  REALAI_ANTHROPIC_API_KEY=sk-ant-...
```

#### 4. Get Your API URL

After deployment completes, look for the output:

```
Outputs:
  RealAIApiUrl: https://xxxxx.execute-api.us-east-1.amazonaws.com/prod/
```

This is your base URL for API calls.

### Testing Lambda Locally

Test before deploying:

```bash
# Start local API
sam local start-api

# Test endpoints
curl http://127.0.0.1:3000/health

curl -X POST http://127.0.0.1:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

### Monitoring

View logs using CloudWatch:

```bash
# Tail logs for a specific function
sam logs -n CoreFunction --stack-name realai-lambda --tail

# View logs for the last 10 minutes
sam logs -n ChatFunction --stack-name realai-lambda --start-time '10min ago'
```

Or use AWS Console:
- **CloudWatch** → **Log groups** → `/aws/lambda/realai-*`

### Cleanup

To delete all Lambda resources:

```bash
sam delete
```

Or via AWS Console:
- **CloudFormation** → **Stacks** → Select `realai-lambda` → **Delete**

### Cost Optimization

Lambda pricing is based on:
- **Requests**: $0.20 per 1M requests
- **Compute time**: $0.0000166667 per GB-second

With the split architecture:
- Each function is optimized for fast cold starts
- Pay only for actual compute time
- No charges when idle

**Example monthly costs** (approximate):
- 100K requests/month: ~$0.20
- 1M requests/month: ~$2-5
- 10M requests/month: ~$20-50

---

## Environment Variables

### Provider API Keys

At least one provider key is required:

| Provider | Environment Variable | Key Prefix | Get Your Key |
|----------|---------------------|------------|--------------|
| OpenAI | `REALAI_OPENAI_API_KEY` | `sk-...` | https://platform.openai.com/api-keys |
| Anthropic | `REALAI_ANTHROPIC_API_KEY` | `sk-ant-...` | https://console.anthropic.com/ |
| xAI/Grok | `REALAI_GROK_API_KEY` | `xai-...` | https://console.x.ai/ |
| Google Gemini | `REALAI_GEMINI_API_KEY` | `AIza...` | https://aistudio.google.com/app/apikey |
| OpenRouter | `REALAI_OPENROUTER_API_KEY` | `sk-or-v1-...` | https://openrouter.ai/keys |
| Mistral AI | `REALAI_MISTRAL_API_KEY` | — | https://console.mistral.ai/api-keys |
| Together AI | `REALAI_TOGETHER_API_KEY` | — | https://api.together.xyz/settings/api-keys |
| DeepSeek | `REALAI_DEEPSEEK_API_KEY` | — | https://platform.deepseek.com/api_keys |
| Perplexity | `REALAI_PERPLEXITY_API_KEY` | `pplx-...` | https://www.perplexity.ai/settings/api |

### Server Configuration (Optional)

```bash
API_HOST=0.0.0.0          # Server host
API_PORT=8000             # Server port
```

---

## Testing Your Deployment

### Health Check

```bash
curl http://localhost:8000/health

# Or for Lambda
curl https://xxxxx.execute-api.us-east-1.amazonaws.com/prod/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "2.1.0"
}
```

### List Models

```bash
curl http://localhost:8000/v1/models
```

### Chat Completion

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ]
  }'
```

### Using with OpenAI SDK

```python
from openai import OpenAI

# Point to your RealAI server
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="any-string-works"  # RealAI uses env vars for actual keys
)

response = client.chat.completions.create(
    model="realai-2.0",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(response.choices[0].message.content)
```

### Connect Third-Party UIs

Any OpenAI-compatible UI can connect to RealAI:

**Examples:**
- [Open WebUI](https://github.com/open-webui/open-webui)
- [ChatBot UI](https://github.com/mckaywrigley/chatbot-ui)
- [LibreChat](https://github.com/danny-avila/LibreChat)

**Configuration:**
- **API Base URL**: `http://localhost:8000/v1` (or your Lambda URL)
- **API Key**: Your provider key (or any string if already set via env vars)
- **Model**: `realai-2.0`

---

## Troubleshooting

### Common Issues

#### "No API key found"

**Problem:** RealAI can't find any provider API keys.

**Solution:**
1. Set at least one provider API key as an environment variable
2. Verify it's set: `echo $REALAI_OPENAI_API_KEY`
3. Restart the server after setting env vars

#### "Connection refused" on localhost:8000

**Problem:** Server not running or port in use.

**Solution:**
```bash
# Check if port is in use
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill process or use different port (use PORT env var)
PORT=8080 python -m realai.api_server
```

#### Lambda deployment fails

**Problem:** AWS credentials not configured or insufficient permissions.

**Solution:**
```bash
# Reconfigure AWS
aws configure

# Check credentials
aws sts get-caller-identity

# Ensure you have Lambda and API Gateway permissions
```

#### Lambda function too large

**Problem:** Function package exceeds 50 MB limit.

**Solution:** The split architecture should prevent this, but if it happens:
1. Check `requirements-lambda-*.txt` files
2. Remove unnecessary dependencies
3. Ensure heavy libraries (sentence-transformers, vosk) are not included
4. Rebuild: `sam build --use-container`

#### Desktop app won't start on Windows

**Problem:** Missing tkinter or dependencies.

**Solution:**
1. Reinstall Python from python.org (not Microsoft Store)
2. During installation, check "tcl/tk and IDLE"
3. Rebuild: `pyinstaller realai_launcher.spec`

#### 502 Bad Gateway from Lambda

**Problem:** Lambda function error or timeout.

**Solution:**
```bash
# Check CloudWatch logs
sam logs -n ChatFunction --stack-name realai-lambda --tail

# Common causes:
# - Missing environment variables
# - Timeout (increase in template.yaml)
# - Cold start issues (first request takes longer)
```

### Getting Help

- **Documentation**: See [README.md](README.md), [API.md](API.md), [QUICKSTART.md](QUICKSTART.md)
- **Lambda Details**: See [LAMBDA_DEPLOYMENT.md](LAMBDA_DEPLOYMENT.md)
- **Issues**: Open an issue on [GitHub](https://github.com/Unwrenchable/realai/issues)

---

## Next Steps

After deployment:

1. **Explore the API**
   - Review [API.md](API.md) for all available endpoints
   - Try the examples in [examples.py](examples.py)

2. **Build Applications**
   - Use RealAI in your Python projects
   - Connect third-party UIs
   - Build custom integrations

3. **Scale Your Deployment**
   - Monitor usage and performance
   - Add more provider API keys for redundancy
   - Configure rate limiting and caching

4. **Stay Updated**
   - Watch the [GitHub repository](https://github.com/Unwrenchable/realai)
   - Check for new features and capabilities
   - Contribute improvements

---

**RealAI** - The limitless AI that can truly do anything. Deploy anywhere, from local development to global cloud infrastructure. 🚀
