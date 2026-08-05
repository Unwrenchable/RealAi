# realai-1.0

RealAI 1.0 **native** weights live here — not API aliases.

## Layout

```
models/realai-1.0/
  manifest.json
  weights/
    realai-1.0-instruct-Q4_K_M.gguf   # produced by training + GGUF export
```

The structured server (`python -m realai.server.app`) resolves `realai-1.0` via
`realai/model_assets.py` and runs inference with `llama-cli` or `llama.cpp`.

Third-party GGUF files (Llama, Qwen, etc.) stay under separate registry IDs such as
`llama-local-1b` or `qwen-coder-7b` with `owned_by` ≠ `realai`.
