import json
from pathlib import Path
from llama_cpp import Llama

# Load model
model = Llama(
    model_path="C:\\RealAI-clean\\realai\\models\\Llama-3.2-1B-Instruct-Q4_K_M.gguf",
    n_gpu_layers=999,
    n_ctx=4096
)

# Load snapshot
snapshot = Path("C:\\RealAI-clean\\results\\repo_snapshot.json").read_text()

# Load architect prompt
prompt = Path("C:\\RealAI-clean\\prompts\\architect_mode.txt").read_text()

# Combine prompt + snapshot
full_prompt = prompt + "\n\n---\n\nRepo Snapshot:\n" + snapshot

# Run inference
output = model(full_prompt, max_tokens=4096)

# Write output
Path("C:\\RealAI-clean\\results\\architect_output.txt").write_text(output["choices"][0]["text"])

print("Architect analysis written.")
