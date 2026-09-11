import json
from pathlib import Path
from realai.core.provider import BaseProvider
from realai.core.llm.gguf_loader import load_gguf_model
from realai.core.llm.peft_loader import load_peft_adapters

class RealAICustomModelProvider(BaseProvider):
    def __init__(self, registry_path):
        self.registry_path = Path(registry_path)
        self.registry = json.loads(self.registry_path.read_text())

        self.root = Path(self.registry["model_root"])
        self.gguf_list = Path(self.registry["gguf_merge_list"])
        self.peft_list = Path(self.registry["lora_adapters_list"])

        self.model = None

    def load(self):
        print("[RealAI Provider] Loading GGUF model...")
        gguf_paths = [line.strip() for line in self.gguf_list.read_text().splitlines()]
        self.model = load_gguf_model(gguf_paths[0])

        print("[RealAI Provider] Applying LoRA adapters...")
        adapter_paths = [line.strip() for line in self.peft_list.read_text().splitlines()]
        load_peft_adapters(self.model, adapter_paths)

        print("[RealAI Provider] Provider ready.")
        return self.model

    def infer(self, prompt, **kwargs):
        return self.model(prompt, **kwargs)
