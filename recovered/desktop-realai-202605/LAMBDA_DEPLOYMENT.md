# RealAI Lambda Deployment

This directory contains the split Lambda function architecture for RealAI, designed to keep each Lambda function under 50 MB to avoid AWS Lambda size limits.

## Architecture Overview

The monolithic API server has been split into 6 separate Lambda functions:

1. **lambda_core** - Core API endpoints (health, models, capabilities)
   - Dependencies: `requests` only (~5 MB)
   - Endpoints: `/health`, `/v1/models`, `/v1/capabilities`

2. **lambda_chat** - Chat and text completions
   - Dependencies: `requests`, `beautifulsoup4` (~10 MB)
   - Endpoints: `/v1/chat/completions`, `/v1/completions`

3. **lambda_image** - Image generation
   - Dependencies: `requests` only (~5 MB)
   - Endpoints: `/v1/images/generations`

4. **lambda_video** - Video generation
   - Dependencies: `requests` only (~5 MB)
   - Endpoints: `/v1/videos/generations`

5. **lambda_embeddings_audio** - Embeddings and audio (routes to external APIs)
   - Dependencies: `requests` only (~5 MB)
   - Endpoints: `/v1/embeddings`, `/v1/audio/transcriptions`, `/v1/audio/speech`
   - **Note**: Heavy local dependencies (sentence-transformers, vosk, pyttsx3) are NOT included. All requests are routed to external provider APIs.

6. **lambda_advanced** - Advanced AI capabilities
   - Dependencies: `requests`, `beautifulsoup4` (~10 MB)
   - Endpoints: `/v1/reasoning/chain`, `/v1/synthesis/knowledge`, `/v1/reflection/analyze`, `/v1/agents/orchestrate`

## Shared Dependencies

Common dependencies are packaged in a Lambda Layer to reduce duplication:
- `requests>=2.28.0`
- `beautifulsoup4>=4.12.0`
- Core `realai.py` module

## Deployment

### Prerequisites

1. Install AWS SAM CLI:
```bash
pip install aws-sam-cli
```

2. Configure AWS credentials:
```bash
aws configure
```

### Deploy All Functions

```bash
# Build all Lambda functions
sam build

# Deploy to AWS
sam deploy --guided
```

Follow the prompts to configure:
- Stack name: `realai-lambda`
- AWS Region: `us-east-1` (or your preferred region)
- Confirm changes before deploy: `Y`
- Allow SAM CLI IAM role creation: `Y`
- Save arguments to configuration file: `Y`

### Deploy Individual Functions

You can also deploy individual functions:

```bash
# Build specific function
sam build CoreFunction

# Deploy
sam deploy
```

## Testing Locally

Test Lambda functions locally using SAM:

```bash
# Start local API
sam local start-api

# Test endpoints
curl http://127.0.0.1:3000/health
curl -X POST http://127.0.0.1:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

## Environment Variables

Set API keys as Lambda environment variables:

```bash
sam deploy --parameter-overrides \
  REALAI_OPENAI_API_KEY=sk-... \
  REALAI_ANTHROPIC_API_KEY=sk-ant-...
```

Or set them in the AWS Console after deployment.

## Size Comparison

**Before (Monolithic)**:
- Total package size: 4.8 GB (exceeded Lambda limits)

**After (Split Architecture)**:
- lambda_core: ~5 MB ✓
- lambda_chat: ~10 MB ✓
- lambda_image: ~5 MB ✓
- lambda_video: ~5 MB ✓
- lambda_embeddings_audio: ~5 MB ✓
- lambda_advanced: ~10 MB ✓
- **All functions under 50 MB zipped limit**

## API Gateway

All functions are exposed through a single API Gateway endpoint, maintaining the same API interface as before.

After deployment, you'll get an API URL like:
```
https://xxxxx.execute-api.us-east-1.amazonaws.com/prod/
```

Use this URL as your base URL for RealAI API calls.

## Monitoring

View logs using CloudWatch:

```bash
sam logs -n CoreFunction --stack-name realai-lambda --tail
```

## Cleanup

To delete all resources:

```bash
sam delete
```

## Migration Notes

### Removed Heavy Dependencies

The following dependencies were removed from Lambda deployment because they're too large:

- `sentence-transformers` (2-3 GB) - Embeddings now route to external APIs (OpenAI, Cohere, etc.)
- `vosk` (1-2 GB) - Audio transcription routes to external APIs (OpenAI Whisper, AWS Transcribe, etc.)
- `pyttsx3` - Text-to-speech routes to external APIs (OpenAI TTS, AWS Polly, etc.)
- `web3` - Blockchain features route to external RPC providers

### Using External APIs

For embeddings, audio, and other heavy features, configure your requests to use external providers:

```python
# Embeddings - use OpenAI
client.embeddings.create(input="text", model="text-embedding-3-small")

# Audio transcription - routes to OpenAI Whisper
client.audio.transcriptions.create(file=audio_file)

# Text-to-speech - routes to OpenAI TTS
client.audio.speech.create(input="text", voice="alloy")
```

All these requests are automatically routed to the appropriate external provider based on your API key.
