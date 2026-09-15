# Self-host provider: `realai`

Self-hosted RealAI declares provider **`realai`**. Local/internal API keys
usually have no cloud prefix (`sk-`, `xai-`, …), so prefix auto-detect cannot
guess OpenAI vs Anthropic vs Grok.

## What the server does

- Explicit `X-Provider` (openai, anthropic, grok, gemini, …) always wins.
- `local` and `realai` are the **same self-host path**; both resolve to
  `REALAI_PROVIDER` (default `realai`). The RealAI constructor still uses
  `provider="local"` for that path.
- Known key prefixes still auto-detect.
- `Authorization: Bearer …` with **no** `X-Provider` (or `auto`) and an
  unrecognized prefix defaults to **`realai`** instead of HTTP 400
  (`Cannot auto-detect provider…`).
- Override the default with env `REALAI_PROVIDER` (default `realai`).

Do not mutate FastAPI `request.headers.__dict__` — this stack is a stdlib
`BaseHTTPRequestHandler`.

## Clients

- Embedded console: dropdown has **RealAI (self-host)** (`realai`) and
  **Local RealAI** (`local`). Both send `X-Provider: realai`. New sessions
  default to `realai`; leftover `auto` in `localStorage` is handled on the
  server (unknown Bearer → `realai`).
- Next UI: set `NEXT_PUBLIC_PROVIDER=realai` next to `NEXT_PUBLIC_API_URL`
  in `frontend/.env.example`. Optional alias: `NEXT_PUBLIC_REALAI_API`.
  Do not commit secrets from `.env.local`.
