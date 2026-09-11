#!/usr/bin/env python3
import json
from pathlib import Path

MODELS_DIR = Path(r"C:\RealAI-clean\models")
OUT = Path(r"C:\RealAI-clean\realai\registry\model_registry.json")

def main():
    entries = []

    for file in MODELS_DIR.iterdir():
        if file.suffix.lower() == ".gguf":
            entries.append({
                "id": file.stem,
                "path": f"models/{file.name}",
                "backend": "llama.cpp",
                "gpu": "amd-vulkan",
                "format": "gguf",
                "enabled": True
            })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"models": entries}, indent=2))

    print(f"[model-registry] wrote {OUT}")

if __name__ == "__main__":
    main()
