#!/usr/bin/env python3
import gzip
import base64
from pathlib import Path
from llama_cpp import Llama

# ---- CONFIG ----
MODEL_PATH = r"C:\RealAI-clean\models\qwen2.5-coder-7b-instruct-q5_k_m.gguf"
PROMPT_PATH = Path(r"C:\RealAI-clean\prompts\architect_mode.txt")
SNAPSHOT_PATH = Path(r"C:\RealAI-clean\results\repo_snapshot.json")
OUT_PATH = Path(r"C:\RealAI-clean\results\architect_output_chunked.txt")

CHUNK_BYTES = 256 * 1024  # 256 KB per chunk
MAX_TOKENS = 1024         # per chunk response


def load_model() -> Llama:
    return Llama(
        model_path=MODEL_PATH,
        n_ctx=4096,
        n_gpu_layers=-1,
    )


def chunk_bytes(data: bytes, size: int):
    for i in range(0, len(data), size):
        yield data[i:i + size]


def build_chunk_prompt(base_prompt: str, chunk_b64: str, idx: int, total: int) -> str:
    return (
        base_prompt
        + f"\n\n---\n\nRepo Snapshot Chunk {idx+1}/{total} (gzip+base64):\n"
        + chunk_b64
        + "\n\nTask: Analyze ONLY this chunk and produce structured findings "
          "about misplaced modules, abilities, plugins, providers, GPU backend, "
          "registry/catalog/world-model issues, and any corrections needed. "
          "Do NOT assume you see the whole repo yet. Just analyze this chunk."
    )


def main() -> int:
    # Load model
    model = load_model()

    # Load architect prompt
    base_prompt = PROMPT_PATH.read_text()

    # Load snapshot as bytes
    snapshot_raw = SNAPSHOT_PATH.read_bytes()

    # Compress once
    snapshot_gzip = gzip.compress(snapshot_raw)

    # Chunk compressed bytes
    chunks = list(chunk_bytes(snapshot_gzip, CHUNK_BYTES))
    total_chunks = len(chunks)

    print(f"[architect_chunked] total compressed size={len(snapshot_gzip)} bytes")
    print(f"[architect_chunked] chunks={total_chunks} (size≈{CHUNK_BYTES} bytes each)")

    all_outputs = []

    for idx, chunk in enumerate(chunks):
        print(f"[architect_chunked] processing chunk {idx+1}/{total_chunks}...")
        chunk_b64 = base64.b64encode(chunk).decode()

        full_prompt = build_chunk_prompt(base_prompt, chunk_b64, idx, total_chunks)

        result = model.create_completion(
            prompt=full_prompt,
            max_tokens=MAX_TOKENS,
            temperature=0.2,
        )

        text = result["choices"][0]["text"]
        all_outputs.append(
            f"\n\n===== CHUNK {idx+1}/{total_chunks} ANALYSIS =====\n{text.strip()}\n"
        )

    # Merge all chunk analyses into one file
    merged = (
        "RealAI Architect Mode — Chunked Repo Analysis\n"
        "Model: qwen2.5-coder-7b-instruct-q5_k_m.gguf\n"
        "Chunks: " + str(total_chunks) + "\n\n"
        + "".join(all_outputs)
    )

    OUT_PATH.write_text(merged, encoding="utf-8")
    print(f"[architect_chunked] wrote merged analysis to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
