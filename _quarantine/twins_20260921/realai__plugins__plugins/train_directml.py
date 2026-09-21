import torch
import torch_directml
from transformers import AutoModelForCausalLM, AutoTokenizer
from torch.optim import AdamW
from torch.utils.data import DataLoader


# -----------------------------
#  DEVICE: DirectML (AMD GPU)
# -----------------------------
dml = torch_directml.device()

# -----------------------------
#  CONFIG
# -----------------------------
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"   # use Qwen on DirectML
DATASET_PATH = "dataset.jsonl"             # your dataset
BATCH_SIZE = 1
LR = 2e-5
MAX_STEPS = 100
SAVE_PATH = "./checkpoints/directml-final.pt"

# -----------------------------
#  LOAD MODEL + TOKENIZER
# -----------------------------
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    dtype=torch.float16,            # DirectML: FP16 only, NOT BF16
    attn_implementation="eager",    # avoid FlashAttention (CUDA-only)
)

# Move model to DirectML
model.to(dml)

# -----------------------------
#  SIMPLE JSONL DATASET
# -----------------------------
class JsonlDataset(torch.utils.data.Dataset):
    def __init__(self, path, tokenizer):
        import json
        with open(path, "r", encoding="utf-8") as f:
            self.samples = [json.loads(l) for l in f]
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        text = self.samples[idx]["text"]
        enc = self.tokenizer(
            text,
            truncation=True,
            max_length=512,
            padding="max_length",
            return_tensors="pt"
        )
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "labels": enc["input_ids"].squeeze(0),
        }


dataset = JsonlDataset(DATASET_PATH, tokenizer)
loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

# -----------------------------
#  OPTIMIZER
# -----------------------------
optimizer = AdamW(model.parameters(), lr=LR)

# -----------------------------
#  TRAIN LOOP
# -----------------------------
step = 0
model.train()

for batch in loader:
    if step >= MAX_STEPS:
        break

    # Move batch to DirectML
    batch = {k: v.to(dml) for k, v in batch.items()}

    outputs = model(**batch)
    loss = outputs.loss

    loss.backward()
    optimizer.step()
    optimizer.zero_grad()

    step += 1
    print(f"Step {step}/{MAX_STEPS} | Loss: {loss.item():.4f}")

# -----------------------------
#  SAVE CHECKPOINT
# -----------------------------
torch.save(model.state_dict(), SAVE_PATH)
print(f"\nSaved DirectML finetuned model → {SAVE_PATH}")
