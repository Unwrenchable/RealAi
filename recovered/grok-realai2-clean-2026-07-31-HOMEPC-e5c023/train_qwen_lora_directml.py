import os
import json
from pathlib import Path
import torch
from datasets import load_dataset
from peft import LoraConfig
from transformers import TrainingArguments

# Unsloth (preferred for big models)
try:
    from unsloth import FastLanguageModel
    UNSLOTH_AVAILABLE = True
except ImportError:
    UNSLOTH_AVAILABLE = False

# Config from env (keeps compatibility with your orchestrator)
MODEL_NAME = os.environ.get("TRAIN_MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")
DATASET_PATH = os.environ.get("TRAIN_DATASET_PATH", "dataset.jsonl")
OUTPUT_DIR = os.environ.get("TRAIN_OUTPUT_DIR", "./checkpoints_lora")
RUN_SUBDIR = os.environ.get("TRAIN_ADAPTER_SUBDIR", "default-run")

# Training params
MAX_STEPS = int(os.environ.get("TRAIN_MAX_STEPS", "200"))
BATCH_SIZE = int(os.environ.get("TRAIN_BATCH_SIZE", "1"))
GRAD_ACCUM = int(os.environ.get("TRAIN_GRADIENT_ACCUMULATION_STEPS", "4"))
LR = float(os.environ.get("TRAIN_LR", "2e-5"))
MAX_LENGTH = int(os.environ.get("TRAIN_MAX_LENGTH", "2048"))

# LoRA
LORA_R = int(os.environ.get("TRAIN_LORA_R", "16"))
# ... etc.

# Device logic
if torch.cuda.is_available():
    device = "cuda"
elif torch_directml.is_available():  # keep your AMD path
    device = torch_directml.device()
else:
    device = "cpu"

print(f"Using device: {device} | Unsloth: {UNSLOTH_AVAILABLE}")

# Load model (Unsloth if available)
if UNSLOTH_AVAILABLE and "cuda" in device:
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_LENGTH,
        dtype=None,  # auto
        load_in_4bit=True,  # QLoRA magic
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_R,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", ...],  # expand for bigger models
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        use_gradient_checkpointing="unsloth",
    )
else:
    # Your existing HF + PEFT path (updated)
    ...

# Dataset (improved)
dataset = load_dataset("json", data_files=DATASET_PATH, split="train")
# Add proper formatting function for chat / instruction

# Training (SFTTrainer or Unsloth trainer)
# ...

# Save adapter
adapter_path = Path(OUTPUT_DIR) / RUN_SUBDIR
model.save_pretrained(adapter_path)
tokenizer.save_pretrained(adapter_path)