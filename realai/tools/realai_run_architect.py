#!/usr/bin/env python3
import gzip
import base64
import json
from pathlib import Path
from llama_cpp import Llama

MODEL_PATH = r"C:\RealAI-clean\models\qwen2.5-coder-7b-instruct-q5_k_m.gguf"
PROMPT_PATH = Path(r"C:\RealAI-clean\prompts\architect_mode.txt")
SNAPSHOT_PATH = Path(r"C:\RealAI-clean\results\repo_snapshot.json")
OUT_PATH = Path(r"C:\RealAI-clean\results\architect_output_chunks.txt")
STATE_PATH = Path(r"C:\RealAI-clean\results\architect_state.json")

MAX_CTX = 4096
TARGET_PROMPT_TOKENS = 2000
MAX_TOKENS = 256

def load_state(total_chunks: int):
    if STATE_PATH.exists():
        try:
            state = json.loads(STATE_PATH.read_text())
            done = set(state.get("done_chunks", []))
            return done
        except Exception:
            return set()
    else:
        STATE_PATH.write_text(json.dumps({"done_chunks": []}, indent=2))
        return set()

def save_state(done_chunks):
    STATE_PATH.write_text(json.dumps({"done_chunks": sorted(done_chunks)}, indent=2))

def main():
    model = Llama(
        model_path=MODEL_PATH,
        n_ctx=MAX_CTX,
        n_gpu_layers=-1
    )

    base_prompt = PROMPT_PATH.read_text()
    snapshot_raw = SNAPSHOT_PATH.read_bytes()
    snapshot_gzip = gzip.compress(snapshot_raw)

    # start with small chunk size; we’ll adjust per chunk
    base_chunk_bytes = 1024

    chunks = [
        snapshot_gzip[i:i+base_chunk_bytes]
        for i in range(0, len(snapshot_gzip), base_chunk_bytes)
    ]
    total_chunks = len(chunks)

    print(f"[architect] compressed={len(snapshot_gzip)} bytes, chunks={total_chunks}")

    done_chunks = load_state(total_chunks)
    outputs = []

    # if we already have output, load it so we can append
    if OUT_PATH.exists():
        outputs.append(OUT_PATH.read_text())

    for idx, raw_chunk in enumerate(chunks):
        chunk_id = idx + 1
        if chunk_id in done_chunks:
            print(f"[architect] chunk {chunk_id}/{total_chunks} (skipped, already done)")
            continue

        print(f"[architect] chunk {chunk_id}/{total_chunks} (processing)")

        # dynamic chunk sizing: shrink until token budget is safe
        chunk_bytes = raw_chunk
        while True:
            chunk_b64 = base64.b64encode(chunk_bytes).decode()
            # build tentative prompt
            prompt = (
                base_prompt +
                f"\n\n---\n\nRepo Snapshot Chunk {chunk_id}/{total_chunks} (gzip+base64):\n" +
                chunk_b64 +
                "\n\nAnalyze ONLY this chunk."
            )
            tokens = model.tokenize(prompt.encode("utf-8"))
            if len(tokens) <= TARGET_PROMPT_TOKENS or len(chunk_bytes) <= 256:
                break
            # shrink chunk
            chunk_bytes = chunk_bytes[: len(chunk_bytes) // 2]

        # final prompt
        full_prompt = prompt

        print(f"[architect] chunk {chunk_id}: prompt_tokens={len(tokens)}, chunk_bytes={len(chunk_bytes)}")

        result = model.create_completion(
            prompt=full_prompt,
            max_tokens=MAX_TOKENS,
            temperature=0.2
        )

        text = result["choices"][0]["text"]
        outputs.append(f"\n\n===== CHUNK {chunk_id}/{total_chunks} =====\n{text.strip()}\n")

        # append to file incrementally
        OUT_PATH.write_text("".join(outputs), encoding="utf-8")

        # update state
        done_chunks.add(chunk_id)
        save_state(done_chunks)

    print(f"[architect] done, wrote {OUT_PATH}")

if __name__ == "__main__":
    main()
