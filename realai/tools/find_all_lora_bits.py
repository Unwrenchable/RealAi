#!/usr/bin/env python3
import os
from pathlib import Path

ROOT = Path(r"C:")

# Keywords that indicate LoRA or training-related files
KEYWORDS = [
    "lora", "adapter", "qlora", "peft", "unsloth", "axolotl",
    "checkpoint", "checkpoints", "trainer", "training", "events",
    "state", "merge", "export", "convert", "apply", "safetensors",
    "gguf", "model", "optimizer", "scheduler"
]

# Extensions commonly used in LoRA training
EXTENSIONS = [
    ".safetensors", ".bin", ".pt", ".ckpt", ".json", ".yaml", ".yml",
    ".jsonl", ".txt", ".log", ".gguf"
]

def is_match(path: Path):
    name = path.name.lower()
    if any(k in name for k in KEYWORDS):
        return True
    if path.suffix.lower() in EXTENSIONS:
        return True
    return False

def main():
    print(f"[search] scanning {ROOT} for ALL LoRA-related bits...\n")

    results = {
        "weights": [],
        "configs": [],
        "datasets": [],
        "logs": [],
        "scripts": [],
        "checkpoints": [],
        "merged_models": [],
        "other": []
    }

    for dirpath, _, filenames in os.walk(ROOT):
        for filename in filenames:
            full = Path(dirpath) / filename
            if not is_match(full):
                continue

            name = filename.lower()

            # classify aggressively
            if any(x in name for x in ["safetensors", "adapter", "weights", "bin", "pt", "ckpt"]):
                results["weights"].append(full)
            elif any(x in name for x in ["yaml", "yml", "config", "json"]):
                results["configs"].append(full)
            elif any(x in name for x in ["dataset", "train", "jsonl"]):
                results["datasets"].append(full)
            elif any(x in name for x in ["log", "tfevents", "trainer_state", "events"]):
                results["logs"].append(full)
            elif any(x in name for x in ["merge", "export", "convert", "apply"]):
                results["scripts"].append(full)
            elif any(x in name for x in ["checkpoint", "checkpoints", "optimizer", "scheduler"]):
                results["checkpoints"].append(full)
            elif any(x in name for x in ["gguf", "merged", "model"]):
                results["merged_models"].append(full)
            else:
                results["other"].append(full)

    # print results
    for category, files in results.items():
        print(f"\n===== {category.upper()} ({len(files)}) =====")
        for f in files:
            print(f)

    print("\n[search] done.")

if __name__ == "__main__":
    main()
