# RealAI Frontend

A professional Next.js 15 chat interface for RealAI.

## Features

- 💬 **Full chat UI** — streaming-style responses, markdown rendering, code blocks
- 🔄 **Conversation history** — persisted in localStorage, grouped by date
- 🧠 **Model selector** — RealAI 2.0, GPT-4o, Claude 3.5 Sonnet, Gemini, and more
- ⚙️ **Settings drawer** — system prompt, temperature slider, max tokens, optional API key
- 📱 **Responsive** — collapsible sidebar, works on mobile
- 🌑 **Dark mode** — slate/indigo design system

## Quick Start (local)

```bash
npm install
cp .env.local.example .env.local   # edit and fill in REALAI_API_BASE + REALAI_API_KEY
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Deploy to Vercel (full-stack — no separate backend needed)

This is the **recommended** deployment. The Next.js `/api/chat` route runs as a
Vercel serverless function and proxies requests directly to any OpenAI-compatible
API, so you need only one Vercel project.

### Step 1 — Import the repository on Vercel

1. Go to [vercel.com/new](https://vercel.com/new) and import this repository.
2. In the **Root Directory** field, enter `realai-frontend`.
3. Leave all other build settings at their defaults.

### Step 2 — Add environment variables

In the Vercel project → **Settings → Environment Variables** add:

| Variable | Example value | Notes |
|---|---|---|
| `REALAI_API_BASE` | `https://openrouter.ai/api` | Base URL of any OpenAI-compatible API (no trailing `/v1`) |
| `REALAI_API_KEY` | `sk-or-v1-...` | Your API key — stored server-side, never sent to the browser |

**Which provider should I use?**

| Goal | `REALAI_API_BASE` | Key |
|---|---|---|
| GPT-4o, Claude, Gemini, Mistral all in one | `https://openrouter.ai/api` | [openrouter.ai/keys](https://openrouter.ai/keys) |
| OpenAI only | `https://api.openai.com` | [platform.openai.com](https://platform.openai.com) |
| Self-hosted Python backend | `https://your-service.onrender.com` | *(from your backend)* |

### Step 3 — Deploy

Click **Deploy**. That's it — both the chat UI and the API route run on Vercel.

---

## Self-hosted Python Backend (optional)

If you want to run the Python API server yourself (adds extra features like
provider auto-detection and the built-in chat UI):

```bash
# From the repo root
pip install -r requirements.txt
python -m realai.api_server   # listens on :8000 by default
```

Then set `REALAI_API_BASE=http://localhost:8000` (or your server's URL) in your
`.env.local` or Vercel env vars.

The Python backend can also be deployed to **Render** using the included
`render.yaml`.

---

## Architecture

```
Browser
  │
  └─► /api/chat  (Next.js serverless function on Vercel)
          │
          └─► REALAI_API_BASE/v1/chat/completions
                  │
                  ├─► https://openrouter.ai/api  (recommended)
                  ├─► https://api.openai.com
                  └─► https://your-service.onrender.com  (self-hosted)
```

API keys never reach the browser — they stay in the serverless function.

## Troubleshooting

- **"Backend URL is not configured"** — make sure `REALAI_API_BASE` is set in Vercel env vars and that you re-deployed after adding it.
- **"Cannot auto-detect provider"** — if using the self-hosted Python backend, select your provider in the Settings drawer or pass `X-Provider` header.
- **Vercel Root Directory** — must be set to `realai-frontend`, not the repo root.
- **No trailing `/v1`** — `REALAI_API_BASE` should be the base origin only (e.g. `https://openrouter.ai/api`, not `https://openrouter.ai/api/v1`).
