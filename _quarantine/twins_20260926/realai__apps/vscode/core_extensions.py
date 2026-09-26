#!/usr/bin/env python3
import json
from pathlib import Path
from typing import List, Dict, Any

# ---------------------------------------------------------------------------
# Shared safe IO
# ---------------------------------------------------------------------------

def safe_read_text(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return default

def safe_read_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []

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

# ---------------------------------------------------------------------------
# Self‑healing GGUF + LoRA auto‑merger
# ---------------------------------------------------------------------------

class GGUFLoRAMerger:
    """
    Tracks GGUF + LoRA lists and writes a merged manifest.
    Does NOT actually merge weights (that’s backend‑specific),
    but gives you a single source of truth for what to load.
    """

    def __init__(self, root: Path):
        self.root = root
        self.gguf_list = root / "gguf_merge_list.txt"
        self.peft_list = root / "peft_merge_list.txt"
        self.manifest = root / "merged_manifest.json"

    def build_manifest(self):
        ggufs = safe_read_lines(self.gguf_list)
        loras = safe_read_lines(self.peft_list)

        data = {
            "gguf_models": ggufs,
            "lora_adapters": loras,
            "preferred_base": ggufs[0] if ggufs else None,
            "adapter_count": len(loras),
        }
        safe_write_json(self.manifest, data)
        print(f"[Merger] manifest built at {self.manifest}")
        return data

# ---------------------------------------------------------------------------
# Self‑healing dataset normalizer
# ---------------------------------------------------------------------------

class DatasetNormalizer:
    """
    Scans for JSON/JSONL datasets under root and writes a combined normalized file.
    If nothing exists, writes an empty file and never crashes.
    """

    def __init__(self, root: Path):
        self.root = root
        self.out_dir = root / "normalized_datasets"
        self.out_file = self.out_dir / "train_combined.jsonl"

    def normalize(self):
        self.out_dir.mkdir(parents=True, exist_ok=True)
        datasets: List[Path] = []

        for p in self.root.rglob("*"):
            if p.suffix in [".json", ".jsonl"]:
                datasets.append(p)

        combined_lines: List[str] = []
        for ds in datasets:
            try:
                text = ds.read_text(encoding="utf-8")
                if ds.suffix == ".jsonl":
                    combined_lines.extend(text.splitlines())
                else:
                    # treat JSON as one example per file
                    obj = json.loads(text)
                    combined_lines.append(json.dumps(obj))
            except Exception:
                continue

        safe_write_text(self.out_file, "\n".join(combined_lines))
        print(f"[Normalizer] wrote {len(combined_lines)} lines to {self.out_file}")
        return self.out_file

# ---------------------------------------------------------------------------
# Self‑healing world‑model visualizer
# ---------------------------------------------------------------------------

class WorldModelVisualizer:
    """
    Produces a simple, human‑readable view of the world‑model state.
    """

    def __init__(self, world_model_path: Path):
        self.path = world_model_path

    def render_text(self) -> str:
        state = safe_read_json(self.path, default={"version": 1, "data": {}})
        lines = [f"WorldModel v{state.get('version', '?')}"]
        for k, v in state.get("data", {}).items():
            lines.append(f"- {k}: {str(v)[:200]}")
        result = "\n".join(lines)
        print("[Visualizer] world‑model snapshot:")
        print(result)
        return result

# ---------------------------------------------------------------------------
# Self‑healing agent router
# ---------------------------------------------------------------------------

class AgentRouter:
    """
    Routes tasks to logical 'agents' based on task type.
    You can plug this into your orchestrator to decide which
    behavior to trigger (analysis, code, memory, world, plugins, etc.).
    """

    def __init__(self):
        self.routes: Dict[str, str] = {
            "code": "code_agent",
            "analysis": "analysis_agent",
            "memory": "memory_agent",
            "world": "world_agent",
            "plugin": "plugin_agent",
            "default": "default_agent",
        }

    def route(self, task: str) -> str:
        task = task.lower()
        for key, agent in self.routes.items():
            if key in task:
                print(f"[AgentRouter] task '{task}' → {agent}")
                return agent
        print(f"[AgentRouter] task '{task}' → default_agent")
        return self.routes["default"]

# ---------------------------------------------------------------------------
# Self‑healing plugin executor
# ---------------------------------------------------------------------------

class PluginExecutor:
    """
    Executes plugin configs from the PluginSystem.
    This is abstract: it just prints what it would do.
    You can wire in subprocess, HTTP calls, etc.
    """

    def __init__(self, plugins_dir: Path):
        self.plugins_dir = plugins_dir

    def execute_all(self):
        for p in self.plugins_dir.glob("*.json"):
            cfg = safe_read_json(p, default={})
            name = cfg.get("name", p.stem)
            ptype = cfg.get("type", "unknown")
            print(f"[PluginExecutor] would execute plugin '{name}' of type '{ptype}' with config: {cfg}")
            # real: branch on type, run trainer, call API, etc.

    def execute(self, name: str):
        cfg_path = self.plugins_dir / f"{name}.json"
        cfg = safe_read_json(cfg_path, default={})
        if not cfg:
            print(f"[PluginExecutor] plugin '{name}' not found")
            return
        ptype = cfg.get("type", "unknown")
        print(f"[PluginExecutor] would execute plugin '{name}' of type '{ptype}' with config: {cfg}")
        # real: branch on type, run trainer, call API, etc.
