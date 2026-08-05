# RealAI — Agent Memory

> **WARNING — NO SECRETS ALLOWED.**
> This file is committed to version control. It must never contain API keys,
> private keys, passwords, RPC credentials, or any other sensitive values.
> Use environment variables or `~/.realai/config.json` (GUI-managed) for secrets.

All additions must be reviewed in a pull request before merging to `main`.

---

## Toolchain decisions

- **Python 3.7+ minimum** — syntax restricted to 3.7 to stay compatible with
  Windows users who may have older interpreters.
- **No pytest/unittest** — tests run directly with `python test_realai.py`
  using plain `assert` statements to avoid test-framework dependencies.
- **BaseHTTPRequestHandler** (stdlib) chosen for the REST server to avoid
  adding a web framework dependency (Flask/FastAPI not required).
- **tkinter** used for the GUI because it ships with the official Python
  installer on all platforms and requires no `pip install`.
- **sentence-transformers** generates real embeddings locally without any API
  key; fallback is a 1536-dimensional zero vector when the library is absent.
- **pyttsx3** is used for TTS because it works offline and cross-platform;
  fallback stub URL returned when unavailable.
- **Vosk** selected for offline speech-to-text; requires user to download and
  point `VOSK_MODEL_PATH` at a model directory.
- **web3.py ≥ 6.0** pinned for the `web3_integration` capability; breaking API
  changes exist between major versions.
- CI matrix: Python 3.11 and 3.12 only (older versions not tested in CI but
  should work given the 3.7+ source constraint).

---

## Commands that worked

| Date | Command | Notes |
|------|---------|-------|
| — | `python test_realai.py` | Runs all 30 tests; no framework needed |
| — | `python api_server.py` | Starts REST server on `localhost:8000` |
| — | `python realai_gui.py` | Launches tkinter GUI |
| — | `python -m realai` | CLI demo using `main()` in realai.py |
| — | `pip install -e .` | Editable install for development |
| — | `pyinstaller realai_launcher.spec` | Builds `dist/RealAI.exe` |
| — | `pip install -r requirements.txt` | Install all runtime deps |
| — | `pip install -r requirements-ci.txt` | Minimal install for CI |

---

## Architecture notes

- **Provider auto-detection** works from API key prefixes (`sk-ant-` →
  Anthropic, `AIza` → Gemini, etc.) — see `_detect_provider()` in `realai.py`.
- **Graceful fallback pattern**: every capability method wraps its real
  implementation in a try/except and returns a structured placeholder dict on
  failure. This is intentional — the framework must never crash on missing deps.
- **OpenAI-compatible facade**: `RealAIClient` mirrors the OpenAI Python
  client interface so existing OpenAI code can be swapped in with minimal edits.
- **Plugin discovery**: `load_all_plugins()` scans the `plugins/` directory for
  Python files and calls each module's `register(model)` function.
- **Code execution sandbox**: uses `resource` module (Linux only) to cap CPU
  and memory. On Windows there are no resource limits — document this clearly
  when exposing `execute_code` in public APIs.
- **REST API key routing**: clients can pass `Authorization: Bearer <key>` and
  optionally `X-Provider: <provider>` to override auto-detection.
- **GUI config path**: `~/.realai/config.json` stores API keys in plaintext.
  The GUI reads/writes this file. Treat it as a secret on shared machines.

---

## Stub capabilities (not yet fully implemented)

| Capability | Method | Current state | Suggested next step |
|---|---|---|---|
| Task automation | `automate_task()` | Returns canned placeholder | Integrate with browser automation (playwright/selenium) or service APIs |
| Voice conversation | `voice_interaction()` | Placeholder only | Wire Vosk STT + pyttsx3 TTS into a real record→transcribe→respond→speak loop |
| Business planning | `business_planning()` | Static template | Call provider with structured system prompt, parse sections from response |
| Therapy support | `therapy_support()` | Template + disclaimer | Call provider with evidence-based CBT system prompt; keep disclaimer prominent |

---

## Gotchas

- **sentence-transformers first run**: downloads ~400 MB model (`all-MiniLM-L6-v2`)
  on first call to `generate_embeddings()`. This can time-out in CI — set
  `SENTENCE_TRANSFORMERS_HOME` to a persistent cache path in production.
- **Vosk model not auto-downloaded**: unlike sentence-transformers, Vosk does
  not auto-download models. Users must manually download a model and set
  `VOSK_MODEL_PATH`. This is a common source of confusion.
- **pyttsx3 on headless servers**: pyttsx3 requires an audio device. On
  headless Linux CI/servers, calls to the TTS engine will fail silently or
  error — the fallback stub handles this correctly.
- **web3.py v6 API**: `web3.eth.get_balance()` returns `Wei` type (not `int`)
  in v6+. Use `web3.from_wei(balance, 'ether')` to convert.
- **Windows resource limits**: the `resource` module is absent on Windows; code
  execution sandbox runs without CPU/memory caps. Add a separate Windows
  guard if this matters for your deployment.
- **API server CORS**: the server adds `Access-Control-Allow-Origin: *` on all
  responses, including errors. Restrict this in production.
- **Provider model names**: model IDs change frequently (e.g. Anthropic
  renamed models in 2024). Update `PROVIDER_CONFIGS` in `realai.py` if you
  receive `model_not_found` errors from a provider.

---

_Add new entries above the relevant section. Keep entries concise._
