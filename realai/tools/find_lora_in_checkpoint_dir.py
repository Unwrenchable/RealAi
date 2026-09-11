#!/usr/bin/env python3
import os
from pathlib import Path

ROOT = Path(r"D:\models\checkpoints_lora")

# LoRA file patterns
LORA_KEYWORDS = [
    "lora", "adapter", "qlora", "peft", "unsloth", "axolotl"
]

LORA_EXTENSIONS = [
    ".safetensors", ".bin", ".json", ".yaml", ".yml", ".jsonl"
]

def is_lora_file(path: Path):
    name = path.name.lower()
    if any(k in name for k in LORA_KEYWORDS):
        return True
    if path.suffix.lower() in LORA_EXTENSIONS:
        return True
    return False

def main():
    print(f"[search] scanning {ROOT} for LoRA-related files...\n")

    results = {
        "weights": [],
        "configs": [],
        "datasets": [],
        "logs": [],
        "scripts": [],
        "other": []
    }

    for dirpath, _, filenames in os.walk(ROOT):
        for filename in filenames:
            full = Path(dirpath) / filename
            if not is_lora_file(full):
                continue

            name = filename.lower()

            # classify
            if any(x in name for x in ["safetensors", "adapter", "weights", "bin"]):
                results["weights"].append(full)
            elif any(x in name for x in ["yaml", "yml", "config", "json"]):
                results["configs"].append(full)
            elif any(x in name for x in ["dataset", "train", "jsonl"]):
                results["datasets"].append(full)
            elif any(x in name for x in ["log", "tfevents", "trainer_state"]):
                results["logs"].append(full)
            elif any(x in name for x in ["merge", "export", "convert", "apply"]):
                results["scripts"].append(full)
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
