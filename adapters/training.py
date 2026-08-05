"""Training adapter — routes core training APIs to promoted + recovered modules."""
from __future__ import annotations
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def list_training_entrypoints() -> dict[str, Path]:
    core_t = ROOT / "core" / "training"
    out: dict[str, Path] = {}
    for name in (
        "finetune.py",
        "build_datasets.py",
        "train_directml.py",
        "train_qwen_lora_directml.py",
        "train_from_agent_manifests.py",
        "eval.py",
    ):
        p = core_t / name
        if p.exists():
            out[name.replace(".py", "")] = p
    datasets = ROOT / "modules" / "training" / "datasets"
    if datasets.exists():
        out["datasets_dir"] = datasets
    return out


def training_status() -> dict[str, Any]:
    eps = list_training_entrypoints()
    return {"available": sorted(k for k in eps if k != "datasets_dir"), "paths": {k: str(v) for k, v in eps.items()}}
