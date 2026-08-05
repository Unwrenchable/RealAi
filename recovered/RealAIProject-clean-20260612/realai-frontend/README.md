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
set NEXT_PUBLIC_REALAI_API_BASE=http://localhost:8000
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Deploy to Render (static frontend)

This frontend now builds as a static export and talks directly to the RealAI
backend from the browser.

### Step 1 — Create the backend on Vercel

Deploy the repository root to Vercel as the Python backend:

1. Go to [vercel.com/new](https://vercel.com/new) and import this repository.
2. Leave the **Root Directory** at the repo root.
3. Set **Framework Preset** to `Other` or `Python`.
4. Add any backend secrets in Vercel.

### Step 2 — Create the frontend on Render

Use Render with the included `render.yaml`:

1. Create a new Static Site from this repository.
2. Render will use `rootDir: realai-frontend`, `buildCommand`, and `publishPath`
   from `render.yaml`.
3. Set `NEXT_PUBLIC_REALAI_API_BASE=https://your-backend.vercel.app`.

### Step 3 — Deploy

Render will publish the static export from `out/`.

---

## Backend

Run the Python API locally or deploy it to Vercel:

```bash
# From the repo root
pip install -r requirements.txt
python -m realai.api_server   # listens on :8000 by default
```

Then set `NEXT_PUBLIC_REALAI_API_BASE=http://localhost:8000`.

---

## Architecture

```
Browser
  │
  └─► NEXT_PUBLIC_REALAI_API_BASE/v1/chat/completions
          │
          └─► https://your-backend.vercel.app
```

## Troubleshooting

- **"Backend URL is not configured"** — make sure `NEXT_PUBLIC_REALAI_API_BASE` is set in Render and that you re-deployed after adding it.
- **No trailing `/v1`** — `NEXT_PUBLIC_REALAI_API_BASE` should be the base origin only (for example `https://your-backend.vercel.app`, not `https://your-backend.vercel.app/v1`).
- **Backend auth** — if your backend expects a bearer token, enter it in the Settings drawer so the browser sends `Authorization: Bearer ...`.
