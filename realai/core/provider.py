import json
from pathlib import Path

def safe_read_lines(path: Path):
    if not path.exists():
        return []
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except:
        return []

def safe_write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def load_gguf_model(path: str):
    print(f"[GGUF] loading {path}")
    return lambda prompt, **kw: f"[GGUF MODEL OUTPUT] {prompt}"

def load_peft_adapters(model, adapters):
    print("[PEFT] applying adapters:")
    for a in adapters:
        print(f"  - {a}")
    return model

class SelfHealingProvider:
    def __init__(self, root: Path):
        self.root = root
        self.gguf_list = root / "gguf_merge_list.txt"
        self.peft_list = root / "peft_merge_list.txt"
        self.model = self._load()

    def _load(self):
        ggufs = safe_read_lines(self.gguf_list)
        if not ggufs:
            print("[provider] no GGUF found, using stub model")
            model = lambda prompt, **kw: f"[STUB MODEL OUTPUT] {prompt}"
        else:
            model = load_gguf_model(ggufs[0])

        adapters = safe_read_lines(self.peft_list)
        if adapters:
            model = load_peft_adapters(model, adapters)

        return model

    def infer(self, prompt: str):
        return self.model(prompt)
