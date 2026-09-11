"""Training adapter — RealAI training assets wired to C:\\models LoRA pipeline."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MODELS = Path(os.environ.get("REALAI_MODELS_DIR") or r"C:\models")
CKPT = MODELS / "checkpoints_lora"


def list_training_entrypoints() -> dict[str, Path]:
    out: dict[str, Path] = {}
    candidates = {
        "lora_directml": ROOT / "core" / "training" / "train_qwen_lora_directml.py",
        "train_from_manifests": ROOT / "core" / "training" / "train_from_agent_manifests.py",
        "finetune_core": ROOT / "core" / "training" / "finetune.py",
        "build_datasets_core": ROOT / "core" / "training" / "build_datasets.py",
        "pipeline": ROOT / "realai" / "training" / "pipeline.py",
        "finetune_realai": ROOT / "realai" / "training" / "finetune.py",
        "build_datasets_realai": ROOT / "realai" / "training" / "build_datasets.py",
        "extract_realai": ROOT / "realai" / "training" / "extract_from_agent_tools.py",
        "unsloth": ROOT / "training" / "unsloth_train.py",
        "wire_training": ROOT / "scripts" / "wire_training.py",
        "dataset_plugins_text": ROOT / "realai" / "plugins" / "dataset.jsonl",
        "dataset_finetune": ROOT / "training" / "data" / "realai_finetune_dataset.jsonl",
        "dataset_ability_surface": ROOT / "training" / "data" / "ability_surface.jsonl",
        "manifests": ROOT / "training" / "data" / "agent_manifests_for_finetuning.json",
        "ready_lora_jsonl": CKPT / "normalized_datasets" / "realai_lora_ready.jsonl",
        "existing_qwen_lora": CKPT / "qwen2.5-1.5b-lora",
    }
    for k, p in candidates.items():
        if p.exists():
            out[k] = p
    datasets = ROOT / "modules" / "training" / "datasets"
    if datasets.exists():
        out["datasets_dir"] = datasets
    return out


def _backend_probe() -> dict[str, Any]:
    info: dict[str, Any] = {
        "inference": "vulkan_llama_server",
        "vulkan_base": os.environ.get("REALAI_VULKAN_BASE", "http://127.0.0.1:8080"),
        "train_prefer": os.environ.get("REALAI_TRAIN_DEVICE") or "auto",
        "cuda": False,
        "directml": False,
        "cpu": True,
    }
    try:
        import torch

        info["torch"] = getattr(torch, "__version__", "?")
        info["cuda"] = bool(torch.cuda.is_available())
    except Exception as e:
        info["torch_error"] = str(e)
    try:
        import torch_directml

        info["directml"] = int(torch_directml.device_count()) > 0
        info["directml_count"] = int(torch_directml.device_count())
    except Exception as e:
        info["directml"] = False
        info["directml_error"] = f"{type(e).__name__}: {e}"
    # Recommended train backend for this machine
    if info["directml"]:
        info["train_backend_recommended"] = "directml"
    elif info["cuda"]:
        info["train_backend_recommended"] = "cuda"
    else:
        info["train_backend_recommended"] = "cpu"
    return info


def training_status() -> dict[str, Any]:
    eps = list_training_entrypoints()
    ready = eps.get("ready_lora_jsonl")
    rows = 0
    if ready and ready.is_file():
        try:
            rows = sum(1 for _ in ready.open(encoding="utf-8", errors="replace"))
        except OSError:
            rows = 0
    adapters = []
    if CKPT.is_dir():
        for cfg in CKPT.glob("*/adapter_config.json"):
            adapters.append(str(cfg.parent))
        for cfg in CKPT.glob("*/*/adapter_config.json"):
            adapters.append(str(cfg.parent))
    return {
        "models_dir": str(MODELS),
        "checkpoints_lora": str(CKPT),
        "available": sorted(eps.keys()),
        "paths": {k: str(v) for k, v in eps.items()},
        "ready_dataset_rows": rows,
        "ready_dataset": str(ready) if ready else None,
        "adapter_dirs_sample": adapters[:20],
        "backends": _backend_probe(),
        "how_to": [
            "python scripts/wire_training.py",
            "python scripts/train_lora_local.py --max-steps 50",
            "python scripts/wire_training.py --start-train --max-steps 50",
            "Chat/inference (AMD Vulkan): keep llama-server on :8080 — not used for LoRA train",
            "python -m realai.training.pipeline --stage status",
        ],
    }
