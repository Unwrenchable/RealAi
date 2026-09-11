#!/usr/bin/env python3
import json
from pathlib import Path

ROOTS = [
    Path(r"C:\models"),
    Path(r"C:\models\checkpoints_lora"),
    Path(r"C:\Users\tsmit\realai"),
    Path(r"C:\Users\tsmit\realai_historical_backups"),
]

def safe_write(path: Path, content: str):
    """Create parent dirs and write safely."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"[ok] wrote: {path}")
    except Exception as e:
        print(f"[warn] could not write {path}: {e}")

def safe_scan(root: Path):
    """Scan directory safely, even if missing or unreadable."""
    if not root.exists():
        print(f"[skip] root missing: {root}")
        return {"gguf": [], "lora": [], "datasets": [], "configs": []}

    gguf = []
    lora = []
    datasets = []
    configs = []

    for p in root.rglob("*"):
        try:
            if p.suffix == ".gguf":
                gguf.append(p)
            elif p.suffix == ".safetensors":
                lora.append(p)
            elif p.suffix in [".json", ".jsonl"]:
                datasets.append(p)
            elif p.suffix in [".yaml", ".yml", ".toml"]:
                configs.append(p)
        except Exception:
            continue

    return {
        "gguf": gguf,
        "lora": lora,
        "datasets": datasets,
        "configs": configs,
    }

def process_root(root: Path):
    print(f"\n=== Processing {root} ===")

    results = safe_scan(root)

    # --- PEFT MERGE LIST ------------------------------------------------------
    peft_list = root / "peft_merge_list.txt"
    if results["lora"]:
        safe_write(peft_list, "\n".join(str(p) for p in results["lora"]))
    else:
        safe_write(peft_list, "")  # empty file is OK
        print("[info] no LoRA adapters found")

    # --- GGUF MERGE LIST ------------------------------------------------------
    gguf_list = root / "gguf_merge_list.txt"
    if results["gguf"]:
        safe_write(gguf_list, "\n".join(str(p) for p in results["gguf"]))
    else:
        safe_write(gguf_list, "")  # empty file is OK
        print("[info] no GGUF models found")

    # --- DATASET NORMALIZATION ------------------------------------------------
    normalized_dir = root / "normalized_datasets"
    normalized_dir.mkdir(exist_ok=True)

    combined_dataset = normalized_dir / "train_combined.jsonl"
    if results["datasets"]:
        combined = []
        for ds in results["datasets"]:
            try:
                for line in ds.read_text(encoding="utf-8").splitlines():
                    combined.append(line)
            except Exception:
                continue
        safe_write(combined_dataset, "\n".join(combined))
    else:
        safe_write(combined_dataset, "")
        print("[info] no datasets found")

    # --- REGISTRY STUB --------------------------------------------------------
    registry = {
        "model_root": str(root),
        "gguf_merge_list": str(gguf_list),
        "lora_adapters_list": str(peft_list),
        "dataset": str(combined_dataset),
        "pipeline": str(root / "finetune_pipeline.json"),
    }
    safe_write(root / "realai_model_registry_stub.json", json.dumps(registry, indent=2))

    # --- FINETUNE PIPELINE ----------------------------------------------------
    pipeline = {
        "base_model": "Qwen2.5-Coder-1.5B-Instruct",
        "dataset": str(combined_dataset),
        "lora_rank": 64,
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
        "output_dir": str(root / "finetune_outputs"),
    }
    safe_write(root / "finetune_pipeline.json", json.dumps(pipeline, indent=2))

def main():
    print("[Self-Healing Pipeline] Starting scan...")
    for root in ROOTS:
        process_root(root)
    print("\n[Self-Healing Pipeline] Completed without crashes.")

if __name__ == "__main__":
    main()
