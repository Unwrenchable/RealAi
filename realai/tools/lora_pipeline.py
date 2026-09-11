#!/usr/bin/env python3
import os
import json
from pathlib import Path

# DIRECTORIES YOU WANT TO SCAN
ROOTS = [
    Path(r"D:\\"),
    Path(r"C:\\")
]

KEYWORDS = [
    "lora", "adapter", "qlora", "peft", "unsloth", "axolotl",
    "checkpoint", "checkpoints", "trainer", "training", "events",
    "state", "merge", "export", "convert", "apply", "safetensors",
    "gguf", "model", "optimizer", "scheduler"
]

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

def scan_all(root: Path):
    print(f"\n[scan] scanning {root} for ALL LoRA-related bits...\n")

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

    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            full = Path(dirpath) / filename
            if not is_match(full):
                continue

            name = filename.lower()

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
            elif any(x in name for x in ["checkpoint", "optimizer", "scheduler"]):
                results["checkpoints"].append(full)
            elif any(x in name for x in ["gguf", "merged", "model"]):
                results["merged_models"].append(full)
            else:
                results["other"].append(full)

    return results

def recover_configs(results):
    print("\n[recover] checking for missing configs...")

    missing = []
    for w in results["weights"]:
        base = w.with_suffix("")
        cfg = base.with_suffix(".json")
        if not cfg.exists():
            missing.append((w, cfg))

    for w, cfg in missing:
        print(f"[recover] missing config for {w.name} → creating {cfg.name}")
        data = {
            "lora_name": w.name,
            "auto_generated": True,
            "rank": 64,
            "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"]
        }
        cfg.write_text(json.dumps(data, indent=2))

def inspect_adapters(results):
    print("\n[inspect] adapter summary:")
    for w in results["weights"]:
        print(f" - {w.name}")

def merge_adapters(results, root: Path):
    print("\n[merge] checking for merge candidates...")
    safes = [p for p in results["weights"] if p.suffix == ".safetensors"]

    if len(safes) < 2:
        print("[merge] not enough adapters to merge.")
        return

    merged = root / "merged_all_adapters.txt"
    print(f"[merge] writing merged list → {merged}")

    merged.write_text("\n".join(str(p) for p in safes))

def generate_report(results, root: Path):
    report = root / "lora_report.txt"
    print(f"\n[report] generating → {report}")

    lines = []
    for cat, files in results.items():
        lines.append(f"\n===== {cat.upper()} ({len(files)}) =====")
        for f in files:
            lines.append(str(f))

    report.write_text("\n".join(lines))

def main():
    for root in ROOTS:
        results = scan_all(root)
        recover_configs(results)
        inspect_adapters(results)
        merge_adapters(results, root)
        generate_report(results, root)

    print("\n[done] Multi-directory LoRA pipeline complete.")

if __name__ == "__main__":
    main()
