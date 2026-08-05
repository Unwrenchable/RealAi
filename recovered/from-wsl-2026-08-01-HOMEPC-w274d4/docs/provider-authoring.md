# Provider Authoring Guide

RealAI providers live under `providers/` and implement the shared interface in `providers/types.ts`.

## Adding a Provider

1. Create a folder in `providers/`.
2. Export a provider object from `index.ts`.
3. Add it to `providers/registry.ts`.

## Best Practices

- Never hardcode API keys.
- Keep provider logic isolated.
- Return plain text content from provider calls.
- Validate required environment variables before sending requests.