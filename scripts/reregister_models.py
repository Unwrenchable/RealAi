from realai.plugins.local_models import LocalModelManager
from pathlib import Path

mgr = LocalModelManager()
models_dir = Path(r"C:\RealAI-clean\models")

registry = [
    ("qwen-coder-7b", "qwen2.5-coder-7b-instruct-q5_k_m.gguf"),
    ("realai-1.0", "realai-1.0-instruct-Q4_K_M.gguf"),
    ("realai-1.0-instruct", "realai-1.0-instruct-Q4_K_M.gguf"),
    ("llama-local", "llama-local-1b-Q4_K_M.gguf"),
    ("llama-3.2-1b", "Llama-3.2-1B-Instruct-Q4_K_M.gguf"),
]

for name, filename in registry:
    path = models_dir / filename
    if not path.exists():
        print(f"SKIP {name}: missing {path}")
        continue
    info = {
        "name": name,
        "type": "llm",
        "backend": "llama-cpp",
        "path": str(path),
        "context_length": 16384,
        "gpu_layers": -1,
        "n_gpu_layers": 99,
        "owned_by": "local",
    }
    ok = mgr.register_model(name, info)
    print(f"register {name}: {ok} -> {path}")

print()
print("Updated list:")
for m in mgr.list_models():
    print(f"  {m['name']}: {m['path']}")
