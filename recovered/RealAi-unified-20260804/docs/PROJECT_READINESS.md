# RealAI — Project Readiness (Whole Stack)

**Goal:** RealAI works as advertised — local native model, self-build, training loop, API, agents, tools — not just the `/ui` playground.

**Last reviewed:** 2026-06-17 (repo @ detached HEAD)

---

## Maturity at a glance

| Layer | Status | Honest summary |
| --- | --- | --- |
| **Inference (GGUF)** | 🟢 Works | `realai.server` + llama-cli / llama.cpp; bootstrap weights |
| **Playground `/ui`** | 🟢 Works | Chat, self-build button, memory panel, streaming UX |
| **Self-builder + repo tools** | 🟡 Partial | Protocol + writes work; **7B/1B model quality** limits success rate |
| **Closed loop (`realai-loop`)** | 🟡 Partial | Pipeline runs; needs server + enough training rows |
| **Training (finetune → export)** | 🟡 Partial | Code complete; **~8 rows in train.jsonl** = not real training yet |
| **Orchestration (planner→…)** | 🔴 Stub | SQLite tasks + **fixed strings**, no LLM calls |
| **Streaming API** | 🟡 Fake stream | Full response generated, then chunked by word (FastAPI path) |
| **Tool auto-exec in chat** | 🟡 Partial | Repo tools only; web3 tools registered not fully wired in router |
| **Embeddings** | 🟡 Basic | Deterministic / stub paths for `realai-embed` |
| **Next.js frontend** | 🟡 Separate | `apps/frontend` — not the same as `/ui`; needs proxy + parity |
| **Cloud providers** | ⚪ Off | `providers.yaml` disabled by design for local-first |
| **CAPABILITIES.md (22 features)** | 🔴 Marketing | Mostly `realai` mega-module stubs, not `realai/server` |
| **Tests** | 🟡 31/36 pass | 2 failures + 3 errors (CLI, protocol prompt text) |
| **Dual servers** | 🔴 Confusing | `realai/server/app.py` **vs** `realai/api_server.py` / GUI |

Legend: 🟢 production-usable for local dev · 🟡 usable with caveats · 🔴 not real yet · ⚪ intentional off

---

## What “badass” means (four loops)

1. **Talk loop** — Chat with **your** GGUF, streaming, tools, memory → **mostly there**
2. **Build loop** — Agent edits repo, runs tests, traces → **there, model-dependent**
3. **Train loop** — Traces → JSONL → finetune → export → bootstrap → **needs data + GPU time**
4. **Product loop** — One server, one UI story, CI green, deploy → **not there**

---

## P0 — Must fix to trust the project (1–2 weeks)

### 1. Single source of truth for runtime

- [ ] **Document:** Primary path = `python -m realai.server.app` only
- [ ] **Deprecate or gate:** `realai/api_server.py`, `api_server.py` root — label “legacy” in README
- [ ] **Align** `apps/frontend` env to same API (`REALAI_API_URL`, `/v1/*`)

### 2. Tests green

```bash
python -m unittest discover -s tests -q
```

Known issues (fix these):

- [ ] `test_agent_protocol` — prompt text changed (“Strict rules” → update test or restore alias in prompt)
- [ ] `test_cli_commands` — `extract-data` command missing from CLI
- [ ] 3 errors in other tests (inspect full log)

### 3. Inference reliability checklist

- [ ] `llama-cli` or `llama-cpp-python` installed and on PATH / in venv
- [ ] `python -m realai.training.pipeline --stage status` — all native chat models **ready**
- [ ] `curl` chat to `realai-1.0-instruct` returns real text, not “Fallback response”
- [ ] Optional: `qwen-coder-7b` GGUF present for **self-build** quality

### 4. Self-build actually completes a task

```bash
# Terminal A
python -m realai.server.app

# Terminal B
export REALAI_API_URL=http://127.0.0.1:8000
realai-build "Run python -m unittest tests.test_agent_protocol -q and report DONE when exit 0"
```

- [ ] Status `done` at least once on a small task
- [ ] `realai/datasets/processed/self_builder_sessions.jsonl` grows

### 5. Training data volume (critical for “self-improving”)

Current: **~8 lines** in `train.jsonl` — not enough.

- [ ] Run `realai-loop --iterations 5` (or more) to grow sessions
- [ ] `python -m realai.training.pipeline --stage datasets` → target **500+** train rows (goal)
- [ ] Then `finetune` → `export` (server **stopped**) → restart server

---

## P1 — Make features match the UI labels (2–4 weeks)

### 6. Real orchestration (not template strings)

**Today:** `realai/server/orchestration.py` writes planner/worker/critic/synthesizer **without calling the model**.

**Target:**

- [ ] Each step calls `chat_completion()` with role-specific system prompts
- [ ] Optional: use `realai-overseer` id when weights ready, else `realai-1.0-instruct`
- [ ] Worker step can invoke `SelfBuilder` or tool runtime for one repo action
- [ ] `/v1/tasks` returns real model outputs in `steps`

### 7. Streaming that is honest

**Today:** FastAPI stream = generate full completion, then emit word chunks.

**Target (pick one):**

- [ ] **A)** UI label: “simulated stream” (quick fix)
- [ ] **B)** Backend: true token/stream from llama-cli if supported (real fix)

### 8. Tool execution path

- [ ] Router `handle_chat_request`: dispatch `web3_solana_rpc`, `web3_evm_call` via `tools_runtime` (not only repo_tools)
- [ ] OpenAI-style `tools` + `tool_calls` round-trip (multi-turn)
- [ ] Document which tools work locally without keys

### 9. Memory as a product feature

- [ ] Chat already stores turns — add **summarization** job (periodic or every N turns) using local model
- [ ] UI “Memory summaries” shows summaries, not raw truncated content
- [ ] Optional: Chroma path in `realai/memory/engine.py` wired to server (today SQLite is primary)

### 10. Playground / product UI

- [ ] Replace Tailwind CDN with built CSS **or** accept dev-only CDN
- [ ] “Clear chat” + “Clear memory” buttons
- [ ] Health badge uses `/health` + model count

---

## P2 — Architecture cleanup (parallel / later)

### 11. Repo consolidation

| Area | Issue | Direction |
| --- | --- | --- |
| `core/` vs `realai/server/` | Duplicate visions | Pick **server** as runtime; migrate or delete unused `core/inference` |
| `apps/api/` | Alternate FastAPI app | Merge routes into `realai/server` or generate OpenAPI from one router |
| `realai/__init__.py` | Huge legacy API | Split or mark deprecated; don’t duplicate CAPABILITIES |
| `models.yaml` vs `registry.json` | Two registries | One loader; other is override only |

### 12. Native model story (real, not bootstrap forever)

- [ ] Fine-tune on **your** self-builder traces (not just Qwen/Llama bootstrap copy)
- [ ] Eval harness: `pipeline --stage eval` gates promotion
- [ ] `realai-overseer` = separate checkpoint when you have data for critique/planning

### 13. CI & release

- [ ] `requirements-ci.txt` + `unittest` + optional `ruff` on PR
- [ ] One `docker compose` path documented and tested
- [ ] Version tag aligns UI (v0.5) + `pyproject` version

### 14. Docs truth pass

- [ ] `CAPABILITIES.md` — tag each capability: **implemented in server** / **stub** / **legacy module only**
- [ ] Point all quickstarts to [COMMANDS_AND_LAYERS.md](COMMANDS_AND_LAYERS.md) + this file

---

## Verification script (run after each milestone)

```bash
# Install
pip install -e . && pip install -r requirements.txt

# Weights
python -m realai.training.pipeline --stage status

# Tests
python -m unittest discover -s tests -q

# Server smoke (background)
python -m realai.server.app &
sleep 2
curl -sf http://127.0.0.1:8000/health
curl -sf http://127.0.0.1:8000/v1/models | python -m json.tool | head -40

# Self-build smoke (server must be up)
export REALAI_API_URL=http://127.0.0.1:8000
realai-loop --check-only

# Data
wc -l realai/datasets/processed/train.jsonl realai/datasets/processed/self_builder_sessions.jsonl
```

**Pass criteria for “P0 complete”:**

- All tests pass (or documented skips only)
- Health + models OK
- `realai-loop --check-only` shows ready chat models
- `train.jsonl` > 100 lines OR explicit decision to train later
- One successful `realai-build` → `done`

---

## Suggested execution order (sprint)

| Week | Focus |
| --- | --- |
| **1** | Tests green, inference smoke, 10× `realai-loop`, grow JSONL |
| **2** | Finetune + export once (GPU), orchestration wired to `chat_completion` |
| **3** | Tools + memory summaries; frontend proxy to server |
| **4** | Doc truth pass, deprecate legacy server, CI |

---

## What you can run **today** for maximum impact

```powershell
# Windows — two terminals
python -m realai.server.app

$env:REALAI_API_URL = "http://127.0.0.1:8000"
$env:REALAI_SELF_IMPROVE = "1"
realai-loop --iterations 10
python -m realai.training.pipeline --stage datasets
python -m unittest discover -s tests -q
```

That combination moves the needle on **build loop + train loop** more than any UI tweak.

---

**See also:** [COMMANDS_AND_LAYERS.md](COMMANDS_AND_LAYERS.md) · [SELF_BUILD_LOCAL.md](SELF_BUILD_LOCAL.md) · [REALAI_NATIVE_MODEL.md](REALAI_NATIVE_MODEL.md)