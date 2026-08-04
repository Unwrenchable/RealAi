# Build RealAI With RealAI (Zero API Spend)

Goal: use **your machine** — local GGUF + `llama-cli` — to edit, test, and evolve this repo like a cloud coding agent, without paying per token.

## 1. Start local inference

```powershell
# If you need to (re)promote weights (e.g. after training a new checkpoint):
#   Stop the server first (Ctrl+C), then:
python -m realai.training.bootstrap_weights

python -m realai.server.app
```

Set:

```powershell
$env:REALAI_API_URL = "http://127.0.0.1:8000"
```

## 2. Run the self-builder

```powershell
realai-build "Add a unit test for self_builder tool parsing"
# or
python -m realai.self_builder "Document the native GGUF pipeline in README"
# or
realai-cli build "Fix realai.toml defaults for local-only mode"
```

The agent picks **`qwen-coder-7b`** when that GGUF is present (best for code), otherwise **`realai-1.0-instruct`**.

## Tools (same idea as this IDE session)

| Tool | Purpose |
| --- | --- |
| `read_file` | Read source before changing |
| `list_dir` | Explore the tree |
| `grep` | Find symbols and config |
| `search_replace` | Apply patches |
| `run_terminal_command` | `unittest`, pipeline status, etc. |

Sessions append to `realai/datasets/processed/self_builder_sessions.jsonl` for future **fine-tune** (self-improving loop).

## 3. Close the circle (server → build → train data)

```powershell
$env:REALAI_SELF_IMPROVE = "1"
realai-loop
# same as: python -m realai.closed_loop
# or one-shot task:
python -m realai.closed_loop --task "Add a test and run unittest"
# Windows:
start_self_build.bat "Improve closed_loop docs"
```

This runs: health check → **self-builder** → ingest `self_builder_sessions.jsonl` → `train.jsonl` / `val.jsonl` → weight status.

Next (when you have GPU time): `python -m realai.training.pipeline --stage finetune` then `--stage export`.

## Config

[`realai.toml`](../realai.toml) section `[self_builder]` — `api_url`, `max_steps`, `timeout`.

`REALAI_WORKSPACE` — repo root (default: project root).

## Limits (honest)

A 1B–7B local model will not match the largest cloud models on every task. Use **qwen-coder-7b** for coding steps; use cloud keys only when you choose (`providers.yaml` keeps APIs **disabled** by default).