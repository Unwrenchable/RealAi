from unsloth import FastLanguageModel
import torch
import json

BASE_MODEL = "Qwen2.5-Coder-1.5B-Instruct"
DATASET = r"C:\models\checkpoints_lora\datasets\normalized_datasets\train_combined.jsonl"
OUTPUT = r"C:\models\checkpoints_lora\finetune_outputs"

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

