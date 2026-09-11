from unsloth import FastLanguageModel
import torch
import json

import os

BASE_MODEL = os.environ.get("TRAIN_MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct")
DATASET = os.environ.get(
    "TRAIN_DATASET_PATH",
    r"C:\models\checkpoints_lora\normalized_datasets\realai_lora_ready.jsonl",
)
OUTPUT = os.environ.get(
    "TRAIN_OUTPUT_DIR",
    r"C:\models\checkpoints_lora\finetune_outputs",
)

def load_dataset(path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]

def main():
    print("[Unsloth] Loading base model...")
    model = FastLanguageModel.from_pretrained(
        BASE_MODEL,
        load_in_4bit=True,
        device_map="auto",
    )

    print("[Unsloth] Applying LoRA...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=64,
        target_modules=["q_proj","k_proj","v_proj","o_proj"],
    )

    print("[Unsloth] Loading dataset...")
    data = load_dataset(DATASET)

    print("[Unsloth] Training...")
    model.train(
        dataset=data,
        output_dir=OUTPUT,
        batch_size=4,
        epochs=3,
        lr=2e-4,
    )

    print("[Unsloth] Training complete.")

if __name__ == "__main__":
    main()
