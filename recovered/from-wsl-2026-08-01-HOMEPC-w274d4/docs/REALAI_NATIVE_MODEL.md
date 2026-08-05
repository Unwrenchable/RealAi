# RealAI as a Native Model (Not a Wrapper)

## The gap you had

| Layer | Before | Now |
| --- | --- | --- |
| `models.yaml` / registry | `realai-1.0` → `realai-fallback` → `RealAI()` → external APIs | `realai-gguf` → on-disk `.gguf` only |
| `registry.json` | `realai-1.0` path = `meta-llama/Meta-Llama-3-8B-Instruct` (vLLM) | `path` = model id; weights under `models/<id>/weights/` |
| Branding | `realai-2.0` default routed to provider default models | `owned_by: realai` requires RealAI weight directories |
| Training | `finetune.py` stub | Same stub + clear artifact layout for GGUF drop |

RealAI remains a **provider** (OpenAI-compatible API, agents, memory, tools). The
**weights** are yours when files live under `models/realai-*`.

## Weight layout

```
models/
  realai-1.0/
    manifest.json
    weights/
      realai-1.0-instruct-Q4_K_M.gguf   # your trained + quantized file
  realai-1.0-instruct/
    manifest.json
    weights/
      ...
  realai-overseer/
    weights/
      ...
```

Resolver: [`realai/model_assets.py`](../realai/model_assets.py)

Environment override: `REALAI_WEIGHTS_ROOT=/path/to/models`

## Run inference (no F16 required)

If you already have a **quantized** GGUF in the repo (e.g. `models/Llama-3.2-1B-Instruct-Q4_K_M.gguf`):

```bash
python -m realai.training.bootstrap_weights
# or: python -m realai.training.pipeline --stage bootstrap
python -m realai.server.app
```

`realai.toml` `[native] auto_bootstrap = true` copies that file into
`models/realai-1.0-instruct/weights/realai-1.0-instruct-Q4_K_M.gguf` on server start when weights are missing.

For production, replace with weights from the fine-tune → export pipeline when ready.

1. Vendored `llama-cli` (`vendor/llama.cpp/b4400/`) or `llama-cpp-python`.
2. Configure [`realai.toml`](../realai.toml) — `default_chat_model = "realai-1.0-instruct"`.
3. Start server: `python -m realai.server.app`

```bash
curl -s http://127.0.0.1:8000/v1/models | jq .
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"realai-1.0","messages":[{"role":"user","content":"ping"}]}'
```

## Dev reference models (not RealAI-branded)

Use explicit IDs — never map these to `realai-1.0`:

- `llama-local-1b` → `models/Llama-3.2-1B-Instruct-Q4_K_M.gguf`
- `qwen-coder-7b` → `models/qwen2.5-coder-7b-instruct-q5_k_m.gguf`

## Roadmap to *your* GGUF binaries

One command per stage (default model id: `realai-1.0-instruct`):

```bash
python -m realai.training.pipeline --stage status
python -m realai.training.pipeline --stage datasets
pip install -r requirements-training.txt
python -m realai.training.pipeline --stage finetune --max-steps 50
# Clone llama.cpp source for convert_hf_to_gguf.py; set REALAI_LLAMA_CPP_ROOT
python -m realai.training.pipeline --stage export
python -m realai.training.pipeline --stage eval --server http://127.0.0.1:8000
```

Or publish an existing GGUF (quantize + copy into `models/<id>/weights/`):

```bash
python -m realai.training.export_gguf --gguf path/to/merged-f16.gguf --model-id realai-1.0-instruct
```

Environment:

| Variable | Purpose |
| --- | --- |
| `REALAI_WEIGHTS_ROOT` | Override `models/` root |
| `REALAI_LLAMA_CPP_ROOT` | llama.cpp checkout (convert script + optional binaries) |
| `REALAI_BASE_HF_MODEL` | HF base for fine-tune (default `meta-llama/Llama-3.2-1B-Instruct`) |

Export also copies the artifact to `realai-1.0/weights/` when publishing instruct weights.
Set `preferred_gguf` in each `manifest.json`; the resolver picks it automatically.

## Self-build without API bills

See [SELF_BUILD_LOCAL.md](SELF_BUILD_LOCAL.md) — `realai-build` uses local GGUF + repo tools to help you evolve RealAI.

## North star (from REALAI_3.0)

- Provider-grade API + **RealAI model family** on local GGUF
- No disguised third-party paths on `owned_by: realai` entries
- Optional cloud providers stay in `providers.yaml` (`enabled: false` by default for local-first)