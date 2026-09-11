#!/usr/bin/env python3
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Callable

# ---------------------------------------------------------------------------
# CONFIG (adjust paths per machine)
# ---------------------------------------------------------------------------

ROOT = Path(r"D:\models\checkpoints_lora")
GGUF_LIST = ROOT / "gguf_merge_list.txt"
PEFT_LIST = ROOT / "peft_merge_list.txt"
WORLD_MODEL_FILE = ROOT / "world_model.json"
MEMORY_FILE = ROOT / "memory_store.json"
PLUGINS_DIR = ROOT / "plugins"

# ---------------------------------------------------------------------------
# GENERIC SAFE IO
# ---------------------------------------------------------------------------

def safe_read_text(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return default

def safe_read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def safe_write_text(path: Path, content: str):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except Exception as e:
        print(f"[warn] write_text failed for {path}: {e}")

def safe_write_json(path: Path, obj: Any):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[warn] write_json failed for {path}: {e}")

def safe_read_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []

# ---------------------------------------------------------------------------
# SELF‑HEALING GGUF LOADER
# ---------------------------------------------------------------------------

def load_gguf_model(path: str) -> Callable[[str], str]:
    print(f"[GGUF] loading {path}")
    # real: load actual GGUF model here
    return lambda prompt, **kw: f"[GGUF MODEL OUTPUT] {prompt}"

class SelfHealingGGUFLoader:
    def __init__(self, gguf_list: Path):
        self.gguf_list = gguf_list
        self.model = self._load_model()

    def _load_model(self):
        paths = safe_read_lines(self.gguf_list)
        if not paths:
            print("[GGUF] no GGUF paths found, using stub model")
            return lambda prompt, **kw: f"[STUB MODEL OUTPUT] {prompt}"
        first = paths[0]
        return load_gguf_model(first)

    def infer(self, prompt: str, **kwargs) -> str:
        return self.model(prompt, **kwargs)

# ---------------------------------------------------------------------------
# SELF‑HEALING LoRA ADAPTER APPLIER
# ---------------------------------------------------------------------------

def load_peft_adapters(model: Callable, adapters: List[str]) -> Callable:
    print("[PEFT] applying adapters:")
    for a in adapters:
        print(f"  - {a}")
    # real: apply adapters to model here
    return model

class SelfHealingLoRAApplier:
    def __init__(self, peft_list: Path, base_model: Callable):
        self.peft_list = peft_list
        self.base_model = base_model
        self.model = self._apply_adapters()

    def _apply_adapters(self):
        adapters = safe_read_lines(self.peft_list)
        if not adapters:
            print("[PEFT] no adapters found, using base model")
            return self.base_model
        return load_peft_adapters(self.base_model, adapters)

    def infer(self, prompt: str, **kwargs) -> str:
        return self.model(prompt, **kwargs)

# ---------------------------------------------------------------------------
# SELF‑HEALING WORLD‑MODEL STORAGE
# ---------------------------------------------------------------------------

class SelfHealingWorldModel:
    def __init__(self, path: Path):
        self.path = path
        self.state = safe_read_json(self.path, default={"version": 1, "data": {}})

    def update(self, key: str, value: Any):
        self.state["data"][key] = value
        safe_write_json(self.path, self.state)
        print(f"[WorldModel] updated {key}")

    def snapshot(self) -> Dict[str, Any]:
        return self.state

# ---------------------------------------------------------------------------
# SELF‑HEALING MEMORY ENGINE
# ---------------------------------------------------------------------------

class SelfHealingMemoryEngine:
    def __init__(self, path: Path):
        self.path = path
        self.store_data = safe_read_json(self.path, default={})

    def store(self, key: str, value: Any):
        self.store_data.setdefault(key, []).append(
            {"ts": time.time(), "value": value}
        )
        safe_write_json(self.path, self.store_data)
        print(f"[Memory] stored under {key}")

    def fetch_recent(self, key: str, limit: int = 5) -> List[Any]:
        entries = self.store_data.get(key, [])
        return [e["value"] for e in entries[-limit:]]

# ---------------------------------------------------------------------------
# SELF‑HEALING PLUGIN SYSTEM
# ---------------------------------------------------------------------------

class SelfHealingPluginSystem:
    def __init__(self, plugins_dir: Path):
        self.plugins_dir = plugins_dir
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.plugins = self._load_plugins()

    def _load_plugins(self) -> Dict[str, Dict[str, Any]]:
        plugins = {}
        for p in self.plugins_dir.glob("*.json"):
            data = safe_read_json(p, default={})
            name = data.get("name", p.stem)
            plugins[name] = data
        print(f"[Plugins] loaded: {list(plugins.keys())}")
        return plugins

    def list_plugins(self) -> List[str]:
        return list(self.plugins.keys())

    def get_plugin(self, name: str) -> Dict[str, Any]:
        return self.plugins.get(name, {})

    def register_plugin(self, name: str, config: Dict[str, Any]):
        self.plugins[name] = config
        safe_write_json(self.plugins_dir / f"{name}.json", config)
        print(f"[Plugins] registered {name}")

# ---------------------------------------------------------------------------
# ONE‑SHOT RUNTIME GLUE: MODEL THAT RUNS ANYWHERE
# ---------------------------------------------------------------------------

class RealAIRuntime:
    """
    Self‑healing runtime that:
    - loads GGUF if available, else stub
    - applies LoRA if available, else base
    - persists world‑model
    - persists memory
    - loads plugins
    """

    def __init__(self):
        self.gguf_loader = SelfHealingGGUFLoader(GGUF_LIST)
        self.lora_applier = SelfHealingLoRAApplier(PEFT_LIST, self.gguf_loader.model)
        self.world = SelfHealingWorldModel(WORLD_MODEL_FILE)
        self.memory = SelfHealingMemoryEngine(MEMORY_FILE)
        self.plugins = SelfHealingPluginSystem(PLUGINS_DIR)

    def infer(self, prompt: str, task: str = "default") -> str:
        self.memory.store("prompts", {"task": task, "prompt": prompt})
        out = self.lora_applier.infer(prompt)
        self.memory.store("outputs", {"task": task, "output": out})
        return out

    def evolve_world_model(self):
        snap = self.world.snapshot()
        out = self.lora_applier.infer(
            f"Given world-model snapshot {snap}, propose improvements."
        )
        self.world.update("evolution", out)

    def reinforce_memory(self):
        recent_errors = self.memory.fetch_recent("errors", limit=5)
        out = self.lora_applier.infer(
            f"Given recent memory errors {recent_errors}, propose reinforcement rules."
        )
        self.memory.store("reinforcement_rules", out)

    def list_plugins(self) -> List[str]:
        return self.plugins.list_plugins()

    def register_plugin(self, name: str, config: Dict[str, Any]):
        self.plugins.register_plugin(name, config)

# ---------------------------------------------------------------------------
# EXAMPLE MAIN (you can call this from anywhere)
# ---------------------------------------------------------------------------

def main():
    runtime = RealAIRuntime()

    print("[Runtime] basic inference:")
    print(runtime.infer("Explain RealAI hive architecture.", task="analysis"))

    print("[Runtime] evolve world-model:")
    runtime.evolve_world_model()

    print("[Runtime] reinforce memory:")
    runtime.reinforce_memory()

    print("[Runtime] plugins:")
    runtime.register_plugin("unsloth_trainer", {"type": "trainer", "script": "unsloth_train.py"})
    print(runtime.list_plugins())

if __name__ == "__main__":
    main()
