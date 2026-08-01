import os
import json
from itertools import cycle
import torch
import torch_directml

from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model
from torch.optim import AdamW


# -----------------------------
#  DEVICE: DirectML (AMD GPU)
# -----------------------------
dml = torch_directml.device()


# -----------------------------
#  CONFIG
# -----------------------------
MODEL_NAME = os.environ.get("TRAIN_MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct")

_TRAIN_DATASET_ENV = os.environ.get("TRAIN_DATASET_PATH", "dataset.jsonl")
_repo_root = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = (
    _TRAIN_DATASET_ENV
    if os.path.isabs(_TRAIN_DATASET_ENV)
    else os.path.normpath(os.path.join(_repo_root, _TRAIN_DATASET_ENV))
)

BATCH_SIZE = int(float(os.environ.get("TRAIN_BATCH_SIZE", "1")))
LR = float(os.environ.get("TRAIN_LR", "5e-5"))
MAX_STEPS = int(float(os.environ.get("TRAIN_MAX_STEPS", "10")))
MAX_LENGTH = int(float(os.environ.get("TRAIN_MAX_LENGTH", "128")))

LORA_R = int(float(os.environ.get("TRAIN_LORA_R", "16")))
LORA_ALPHA = int(float(os.environ.get("TRAIN_LORA_ALPHA", "32")))
LORA_DROPOUT = float(os.environ.get("TRAIN_LORA_DROPOUT", "0.05"))

_target_modules_env = os.environ.get("TRAIN_LORA_TARGET_MODULES", "q_proj,k_proj,v_proj,o_proj")
LORA_TARGET_MODULES = [m.strip() for m in _target_modules_env.split(",") if m.strip()]

OUTPUT_DIR = os.environ.get("TRAIN_OUTPUT_DIR", "./checkpoints_lora")
run_subdir = os.environ.get("TRAIN_ADAPTER_SUBDIR", "qwen2.5-1.5b-lora")
_output_root = OUTPUT_DIR
os.makedirs(_output_root, exist_ok=True)



# -----------------------------
#  TOKENIZER + BASE MODEL
# -----------------------------
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    dtype=torch.float16,            # DirectML: FP16
    attn_implementation="eager",    # avoid FlashAttention
)

# LoRA CONFIG
lora_config = LoraConfig(
    r=LORA_R,
    lora_alpha=LORA_ALPHA,
    lora_dropout=LORA_DROPOUT,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=LORA_TARGET_MODULES,
)

model = get_peft_model(model, lora_config)
model.config.use_cache = False

# === Add these for memory savings ===
import torch

# Lower precision
model = model.to(dtype=torch.float16)

# Critical: Gradient checkpointing
model.gradient_checkpointing_enable()

# Disable cache during training
model.config.use_cache = False

# Optional: Reduce memory fragmentation
torch.backends.cuda.matmul.allow_tf32 = True
# For DirectML you can also try:
# os.environ["PYTORCH_DIRECTML_MEMORY_LIMIT"] = "0"

# MEMORY + DEVICE
model.gradient_checkpointing_enable()
model = model.to(dml).half()
torch.set_grad_enabled(True)

print("\nTrainable parameters (LoRA only):")
model.print_trainable_parameters()


# -----------------------------
#  DATASET
# -----------------------------
class JsonlTextDataset(Dataset):
    def __init__(self, path, tokenizer, max_length: int):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.samples = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                text = obj.get("text", "").strip()
                if text:
                    self.samples.append(text)

        if not self.samples:
            raise ValueError(f"No valid 'text' entries found in {path}")

        print(f"Loaded {len(self.samples)} samples from {path}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        text = self.samples[idx]
        if hasattr(self.tokenizer, "apply_chat_template"):
            text = self.tokenizer.apply_chat_template(
                [{"role": "assistant", "content": text}],
                tokenize=False,
                add_generation_prompt=False,
            )
        enc = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        input_ids = enc["input_ids"].squeeze(0)
        attention_mask = enc["attention_mask"].squeeze(0)

        labels = input_ids.clone()
        labels[attention_mask == 0] = -100

        # Avoid training on padding-like labels: ensure we never backprop through ignored tokens.
        # Some tokenizers/templates can emit pad/eos combinations; keep them ignored.
        if tokenizer.pad_token_id is not None:
            labels[input_ids == tokenizer.pad_token_id] = -100
        elif tokenizer.eos_token_id is not None:
            labels[input_ids == tokenizer.eos_token_id] = -100



        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


dataset = JsonlTextDataset(DATASET_PATH, tokenizer, MAX_LENGTH)
loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)


# -----------------------------
#  OPTIMIZER
# -----------------------------
# DirectML compatibility: AdamW can trigger unsupported ops (e.g. aten::lerp.Scalar_out) -> CPU fallback -> NaNs.
# Use SGD for stability on DirectML.
optimizer = torch.optim.SGD(model.parameters(), lr=LR)



# -----------------------------
#  TRAIN LOOP
# -----------------------------
model.train()
step = 0

for batch in cycle(loader):
    if step >= MAX_STEPS:
        break

    batch = {k: v.to(dml) for k, v in batch.items()}

    outputs = model(**batch)
    loss = outputs.loss

    # Safety: stop early if loss diverges into NaN/Inf (common on some DirectML configs)
    try:
        loss_val = float(loss.item())
    except Exception:
        loss_val = float('nan')

    if not (loss_val == loss_val) or loss_val in (float('inf'), float('-inf')):
        print(f"[train_qwen_lora_directml] Non-finite loss detected at step={step} loss={loss_val}. Stopping run.")
        break

    loss.backward()
    optimizer.step()
    optimizer.zero_grad()

    step += 1
    if step % 10 == 0 or step == 1:
        print(f"Step {step}/{MAX_STEPS} | Loss: {loss_val:.4f}")


# -----------------------------
#  SAVE LoRA ADAPTER (CPU)
# -----------------------------
adapter_path = os.path.join(OUTPUT_DIR, run_subdir)


# Move to CPU to avoid OpaqueTensorImpl issues on DirectML
model_cpu = model.to("cpu").float()

model_cpu.save_pretrained(adapter_path)
tokenizer.save_pretrained(adapter_path)

print(f"\nSaved LoRA adapter → {adapter_path}")
print("To use it later, load base model + adapter with PEFT.")
