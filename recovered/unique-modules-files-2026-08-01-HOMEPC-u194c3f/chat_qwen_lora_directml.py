import torch
import torch_directml
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from typing import Optional

# Define device for DirectML
def get_directml_device() -> torch.device:
    """Get DirectML device."""
    try:
        return torch_directml.device()
    except torch_directml.TorchDirectMLError as e:
        print(f"Failed to initialize DirectML device: {e}")
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Define model and tokenizer
def load_model_and_tokenizer(base_model: str, adapter_path: str) -> tuple:
    """Load model and tokenizer."""
    dml = get_directml_device()
    tokenizer = AutoTokenizer.from_pretrained(adapter_path)
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model,
        dtype=torch.float16,
        attn_implementation="eager",
    )
    model = PeftModel.from_pretrained(base_model, adapter_path)
    model = model.half()
    model = model.to(dml)
    model.config.use_cache = False
    model.eval()
    return model, tokenizer

# Define main loop
def main():
    import os

    BASE_MODEL = os.environ.get("BASE_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
    ADAPTER_SUBDIR = os.environ.get("ADAPTER_SUBDIR", "qwen2.5-1.5b-lora-smoke-test")
    ADAPTER_PATH = os.path.join("./checkpoints_lora", ADAPTER_SUBDIR)

    model, tokenizer = load_model_and_tokenizer(BASE_MODEL, ADAPTER_PATH)

    while True:
        prompt = input("\nYou: ")
        if not prompt.strip():
            continue
        if prompt.strip().lower() in {"exit", "quit"}:
            break

        try:
            inputs = tokenizer(prompt, return_tensors="pt").to(get_directml_device())
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=128,
                    do_sample=False,  # keep greedy (DirectML-safe)
                    use_cache=False,
                    no_repeat_ngram_size=6,  # block obvious loops
                    repetition_penalty=1.2,  # discourage repeating same token
                )
            print("\nModel:", tokenizer.decode(outputs[0], skip_special_tokens=True))
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()