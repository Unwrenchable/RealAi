#!/usr/bin/env python3
"""
create_training_runs_json.py - Fixed & hardened version
Generates agent_manifests_for_finetuning_training_runs.json
in the exact schema expected by your training runner.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

try:
    REPO_ROOT = Path(__file__).parent.resolve()
    OUT_FILE = REPO_ROOT / "agent_manifests_for_finetuning_training_runs.json"

    BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
    DATASET_PATH = "dataset.jsonl"
    LORA_TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj"]

    def make_run(run_id: str, lr: float, max_steps: int, r: int = 16, alpha: int = 32,
                 dropout: float = 0.05, max_length: int = 2048, batch_size: int = 1,
                 output_subdir: str = None):
        if output_subdir is None:
            output_subdir = run_id
        return {
            "id": run_id,
            "model_name": BASE_MODEL,
            "dataset_path": DATASET_PATH,
            "output_dir": "./checkpoints_lora",
            "lora": {
                "r": r,
                "alpha": alpha,
                "dropout": dropout,
                "target_modules": LORA_TARGETS
            },
            "training": {
                "lr": lr,
                "max_steps": max_steps,
                "batch_size": batch_size,
                "max_length": max_length
            },
            "adapter_subdir": output_subdir
        }

    def main():
        runs = []

        # Run 0: Quick smoke test (very safe, fast)
        runs.append(make_run(
            run_id="qwen2.5-1.5b-lora-smoke-test",
            lr=5e-6,
            max_steps=20,
            r=16,
            max_length=1024
        ))

        # Run 1: Main full-stack abilities (recommended)
        runs.append(make_run(
            run_id="qwen2.5-1.5b-lora-full-stack-abilities-v1",
            lr=1.5e-5,
            max_steps=300,
            r=24,
            alpha=48,
            dropout=0.06,
            max_length=3072
        ))

        # Run 2: Deeper stacking
        runs.append(make_run(
            run_id="qwen2.5-1.5b-lora-deeper-stack-v2",
            lr=8e-6,
            max_steps=200,
            r=32,
            alpha=64,
            dropout=0.05,
            max_length=4096
        ))

        # Run 3: Long-context orchestration
        runs.append(make_run(
            run_id="qwen2.5-1.5b-lora-orchestration-longctx",
            lr=1e-5,
            max_steps=150,
            r=20,
            alpha=40,
            max_length=4096
        ))

        with OUT_FILE.open("w", encoding="utf-8") as f:
            json.dump(runs, f, indent=2, ensure_ascii=False)

        print(f"✅ SUCCESS: Created {OUT_FILE} with {len(runs)} training runs")
        print("\nNext commands (run in Command Prompt):")
        print("   set AGENT_MANIFESTS_FOR_FINETUNING_PATH=agent_manifests_for_finetuning_training_runs.json")
        print("   set TRAIN_ONLY_INDEX=0")
        print("   python train_from_agent_manifests.py")
        print("\nAfter the smoke test works (no NaN, adapter saved), remove the TRAIN_ONLY_INDEX line (or change the number) to run the full stacking runs.")

    if __name__ == "__main__":
        main()

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)