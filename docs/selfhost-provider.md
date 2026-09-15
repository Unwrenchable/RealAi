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

## Cloud UI vs Local Hive

`X-Provider: realai` is the **product identity**, not a promise that this
process has a GGUF.

| Surface | Process | GPU / GGUF | `default_llm` |
|---------|---------|------------|----------------|
| **Cloud UI** (Vercel → Render) | `python -m realai.api_server` | **None.** Render has no Vulkan and no `C:\\models\\checkpoints_lora`. | Not used. If no cloud key, chat explains Cloud vs Hive — it does **not** tell you to register a PC registry. |
| **Local Hive** (PC console `:8001`) | `python -m realai.v3_orchestrator` + loopback llama-server `:8080` | Vulkan GGUF on the PC | Set `default_llm` in **`~/.realai/local_models.json`** (what `LocalModelManager` loads). |

**Which file is which**

- **`~/.realai/local_models.json`** — runtime registry for `api_server` / `RealAI.chat_completion`. `default_llm` + model `path` must exist on **this** machine.
- **`C:\\models\\checkpoints_lora\\registry.json`** — PC-only Hive/Vulkan weight index. Cloud UI / Render **never** reads it.
- **`realai/config/models.json`** — checked-in local catalog (docs). Not loaded on Render. Paths are `C:/models/checkpoints_lora/…`; Linux CI must not require those files.

On Render, `provider=realai` with no local GGUF **falls back** to
`OPENAI_API_KEY` / `REALAI_OPENAI_API_KEY` / other `REALAI_*_API_KEY`, or
`REALAI_CLOUD_FALLBACK=<provider>`. Set `REALAI_CLOUD_FALLBACK=off` to refuse
that. Vulkan forward (`REALAI_VULKAN_FORWARD`) is **loopback Hive only** —
disabled on Render.

If there is no GGUF and no cloud key, the reply names Local Hive
(`NEXT_PUBLIC_LOCAL_CONSOLE_URL` or `http://127.0.0.1:8001/console`) and
cloud keys — not “register default_llm”.

## Clients

- Embedded console: dropdown has **RealAI (self-host)** (`realai`) and
  **Local RealAI** (`local`). Both send `X-Provider: realai`. New sessions
  default to `realai`; leftover `auto` in `localStorage` is handled on the
  server (unknown Bearer → `realai`).
- Next UI: set `NEXT_PUBLIC_PROVIDER=realai` next to `NEXT_PUBLIC_API_URL`
  in `frontend/.env.example`. Optional alias: `NEXT_PUBLIC_REALAI_API`.
  Optional `NEXT_PUBLIC_LOCAL_CONSOLE_URL` (PC console link).
  Do not commit secrets from `.env.local`.
