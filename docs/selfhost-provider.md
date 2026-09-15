# Self-host provider: `realai`

Self-hosted RealAI declares provider **`realai`**. Local/internal API keys
usually have no cloud prefix (`sk-`, `xai-`, …), so prefix auto-detect cannot
guess OpenAI vs Anthropic vs Grok.

## What the server does

- Explicit `X-Provider` (openai, anthropic, grok, gemini, …) always wins.
- Known key prefixes still auto-detect.
- `Authorization: Bearer …` with **no** `X-Provider` and an unrecognized
  prefix defaults to **`realai`** instead of HTTP 400
  (`Cannot auto-detect provider…`).
- Override the default with env `REALAI_PROVIDER` (default `realai`).

Do not mutate FastAPI `request.headers.__dict__` — this stack is a stdlib
`BaseHTTPRequestHandler`.

## Clients

- Embedded console: provider dropdown defaults to **RealAI (self-host)** and
  sends `X-Provider: realai`.
- Next UI: set `NEXT_PUBLIC_PROVIDER=realai` and
  `NEXT_PUBLIC_REALAI_API` (or `NEXT_PUBLIC_API_URL`) in `.env.example`.
  Do not commit secrets from `.env.local`.
