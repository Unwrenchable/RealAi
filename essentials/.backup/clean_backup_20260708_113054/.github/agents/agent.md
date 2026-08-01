# RealAI — Agent Guidance

Use this file to orient yourself before suggesting changes to RealAI.

## Project overview

**RealAI** is a unified Python AI framework providing 17 capabilities through
a single OpenAI-compatible interface. It routes requests to 9 external AI
providers, exposes a REST API server, a tkinter GUI, and a command-line tool.
The goal is "the limitless AI that can truly do anything."

## Repository layout

```
/                          # Repo root
├── realai.py              # Core model: RealAI + RealAIClient classes (1,571 lines)
├── api_server.py          # REST API server (BaseHTTPRequestHandler, port 8000)
├── realai_gui.py          # tkinter GUI: key management, chat panel, server control
├── __init__.py            # Package init: exports RealAI, RealAIClient, etc.
├── setup.py               # Package metadata (v2.0.0, Python ≥ 3.7)
├── requirements.txt       # Runtime deps (requests, beautifulsoup4, etc.)
├── requirements-ci.txt    # CI-only deps (requests, beautifulsoup4)
├── test_realai.py         # 30 assertion-based tests (no pytest/unittest framework)
├── examples.py            # Original usage examples
├── examples_limitless.py  # Extended capability examples
├── realai_launcher.spec   # PyInstaller spec for standalone RealAI.exe
├── plugins/               # Plugin system
│   ├── __init__.py
│   └── sample_plugin.py   # Example plugin showing registration pattern
└── .github/
    ├── workflows/ci.yml   # CI: Python 3.11 + 3.12, ubuntu-latest
    └── agents/            # This directory
```

## Toolchain

| Layer | Tool |
|-------|------|
| Language | Python 3.7–3.12 |
| HTTP requests | `requests` ≥ 2.28 |
| Web scraping | `beautifulsoup4` ≥ 4.12 |
| Embeddings | `sentence-transformers` ≥ 2.2.2 |
| Text-to-speech | `pyttsx3` ≥ 2.90 |
| Speech-to-text | `vosk` ≥ 0.3.45 (requires separate model download) |
| Blockchain | `web3` ≥ 6.0.0 |
| GUI | `tkinter` (stdlib, ships with Python) |
| Packaging | `PyInstaller` (for `.exe` builds) |
| CI | GitHub Actions (`.github/workflows/ci.yml`) |

## Key scripts

```bash
# Run all tests (no framework required — plain assertions)
python test_realai.py

# Start REST API server
python api_server.py

# Launch GUI
python realai_gui.py

# CLI demo
python -m realai

# Install in editable mode (for development)
pip install -e .

# Build Windows executable
pyinstaller realai_launcher.spec
```

## Core class hierarchy

```
realai.py
├── ModelCapability (Enum)        # 17 capability constants
├── PROVIDER_CONFIGS (dict)       # Per-provider URL / model defaults
├── PROVIDER_ENV_VARS (dict)      # Env var names for each provider
└── RealAI                        # Central model class
    ├── _detect_provider()        # Auto-detect from API key prefix
    ├── _make_api_request()       # Shared HTTP call to any provider
    ├── chat_completion()         # Core chat method
    ├── generate_image()          # Image generation
    ├── analyze_image()           # Vision / image analysis
    ├── generate_embeddings()     # sentence-transformers or stub
    ├── transcribe_audio()        # Vosk ASR or stub
    ├── generate_speech()         # pyttsx3 TTS or stub
    ├── translate()               # Translation via provider
    ├── web_research()            # DuckDuckGo + BeautifulSoup
    ├── automate_task()           # ⚠ STUB
    ├── voice_interaction()       # ⚠ STUB
    ├── business_planning()       # ⚠ STUB
    ├── therapy_support()         # ⚠ STUB (with disclaimer)
    ├── web3_integration()        # web3.py read-only or stub
    ├── execute_code()            # sandboxed Python exec
    └── plugin_system()           # load_plugin / load_all_plugins

RealAIClient                      # OpenAI-compatible client facade
├── .chat                         # .create()
├── .completions                  # .create()
├── .images                       # .generate() / .analyze()
├── .embeddings                   # .create()
├── .audio                        # .transcribe() / .generate()
├── .web                          # .research()
├── .tasks                        # .automate() / .order_groceries() / .book_appointment()
├── .voice                        # .conversation()
├── .business                     # .build()
├── .therapy                      # .support()
├── .web3                         # .smart_contract() / .deploy() / .query()
└── .plugins                      # .load() / .load_all_plugins()
```

## 9 supported AI providers and their API key prefixes

| Provider | Key prefix | Default model |
|---|---|---|
| OpenAI | `sk-proj-` or `sk-` | `gpt-4o-mini` |
| Anthropic | `sk-ant-` | `claude-3-5-haiku-20241022` |
| xAI/Grok | `xai-` | `grok-beta` |
| Google Gemini | `AIza` | `gemini-1.5-flash` |
| OpenRouter | `sk-or-` | `openai/gpt-4o-mini` |
| Mistral | `mis-` | `mistral-small-latest` |
| Together AI | `tog-` | `togethercomputer/llama-3-8b-chat-hf` |
| DeepSeek | `dsk-` | `deepseek-chat` |
| Perplexity | `pplx-` | `llama-3.1-sonar-small-128k-online` |

## Environment variables

```bash
# Provider API keys (at least one required for real responses)
REALAI_OPENAI_API_KEY
REALAI_ANTHROPIC_API_KEY
REALAI_GROK_API_KEY
REALAI_GEMINI_API_KEY
REALAI_OPENROUTER_API_KEY
REALAI_MISTRAL_API_KEY
REALAI_TOGETHER_API_KEY
REALAI_DEEPSEEK_API_KEY
REALAI_PERPLEXITY_API_KEY

# Optional capability enablers
WEB3_PROVIDER_URL          # Ethereum/EVM RPC endpoint (e.g. Infura, Alchemy)
VOSK_MODEL_PATH            # Path to downloaded Vosk ASR model directory
```

## Coding conventions

- **Python 3.7+ compatible** — avoid walrus operator (`:=`), `match` statement, etc.
- **Type hints** on all public methods (follow existing patterns in `realai.py`)
- **Docstrings** on all public classes and methods (Google style)
- **Graceful fallback** — every capability must return a useful response even
  when optional dependencies are missing or the network is unavailable
- **PEP 8** formatting; no line length limit enforced in CI
- **No external test framework** — tests use plain `assert` statements; add new
  tests to `test_realai.py` following the `test_*` naming convention
- **No secrets in code** — API keys only via environment variables or headers
- **Plugin pattern** — new capabilities that depend on optional third-party
  services should be implemented as plugins in `plugins/`

## Known stub implementations (priority targets for improvement)

1. `automate_task()` / `tasks.automate()` — returns canned placeholder; needs
   real integration (browser automation, service APIs, etc.)
2. `voice_interaction()` / `voice.conversation()` — stub; pyttsx3 + Vosk wired
   separately but not combined into a real turn-taking conversation loop
3. `business_planning()` / `business.build()` — returns static template; should
   call a provider and do structured analysis
4. `therapy_support()` / `therapy.support()` — returns template + disclaimer;
   should call a provider with a carefully crafted system prompt

## REST API endpoints (port 8000 by default)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/v1/models` | List models |
| GET | `/v1/models/<id>` | Model detail |
| POST | `/v1/chat/completions` | Chat (OpenAI-compatible) |
| POST | `/v1/completions` | Text completion |
| POST | `/v1/images/generations` | Image generation |
| POST | `/v1/embeddings` | Embeddings |
| POST | `/v1/audio/transcriptions` | Speech-to-text |
| POST | `/v1/audio/speech` | Text-to-speech |


## Toolchain

| Layer | Tool |
|-------|------|
| EVM contracts | Solidity 0.8.20+, Hardhat 2.17, OpenZeppelin 5 |
| TypeScript compilation | `tsc` (root), `tsc -p tsconfig.json` (relayer) |
| Contract testing | Hardhat + Mocha + Chai |
| Linting | ESLint with `@typescript-eslint` |
| Frontend build | Vite 5 + React 18 |
| Solana program | Rust + `cargo build-bpf` |
| Containerisation | Docker + docker-compose |

## Root `package.json` scripts

```
build              tsc
test               hardhat test
lint               eslint . --ext .ts,.js
compile-contracts  hardhat compile
deploy-evm         hardhat run scripts/deploy-evm.ts
build-solana       cargo build-bpf --manifest-path=programs/fizzdex-solana/Cargo.toml
relayer:init-mappings  node relayer/init-mappings.js
```

## Relayer scripts (`relayer/package.json`)

```
start        ts-node src/index.ts
build        tsc -p tsconfig.json
start:prod   node dist/index.js
```

## Web scripts (`web/package.json`)

```
dev      vite
build    vite build
preview  vite preview
```

## Key conventions

- **Security**: All state-changing Solidity functions use reentrancy guards;
  Solidity 0.8.20+ for overflow protection. See `SECURITY.md`.
- **Chain adapter pattern**: `src/chain-adapter.ts` exports an `IChainAdapter`
  interface that every chain integration must implement.
- **Frontend env vars**: Vite convention — prefix with `VITE_`. Declared in
  `web/src/vite-env.d.ts`. Available vars: `VITE_SOLANA_RPC`,
  `VITE_SOLANA_PROGRAM_ID`, `VITE_RELAYER_URL`. Template: `web/.env.example`.
- **Browser polyfills**: `vite-plugin-node-polyfills` supplies Buffer/process/
  crypto shims. The web UI uses the Web Crypto API (not Node's `crypto`).
- **Single-component UI**: All state and logic lives in `web/src/App.tsx`.
  Four tabs: swap / pool / fizzcaps / bridge.
- **Secrets**: Never committed. Use `.env` files (git-ignored). Templates are
  `.env.example` files.

## Things to watch out for

- `minOut` is currently hardcoded to `0` in swap logic — slippage is not
  enforced on-chain even though the UI shows fee/slippage info.
- The web bundle will emit a large-chunk warning (>500 KB) from ethers +
  `@solana/web3.js` — this is expected.
- Vercel deployment is configured via `vercel.json` at the root; build command
  is `cd web && npm install && npm run build`; output dir is `web/dist`.
- `relayer-mappings.json` is git-ignored (generated at runtime by
  `relayer:init-mappings`).
