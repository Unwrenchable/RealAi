# Model Manifest Guide

RealAI model manifests live in `models/<model-name>/manifest.json`.

## Manifest Shape

```json
{
  "name": "realai-1.0",
  "version": "1.0.0",
  "provider": "realai",
  "context": 128000,
  "type": "text",
  "description": "General-purpose reasoning model.",
  "capabilities": ["chat", "reasoning", "summarization"]
}
```

## Adding a Model

1. Create a folder in `models/`.
2. Add `manifest.json`.
3. Add the model package manifest if you want it detected by pnpm workspace tooling.