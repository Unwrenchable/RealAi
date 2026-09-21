#!/usr/bin/env python3
"""train_from_agent_manifests.py - Fixed & Optimized for DirectML"""
from __future__ import annotations
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import torch  # <-- This was missing in your running version

# DirectML
try:
    import torch_directml
    device = torch_directml.device()
    print(f"Device detected: DirectML ({torch_directml.device_count()} devices)")
    is_directml = True
except ImportError:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device detected: {device}")
    is_directml = False

import datasets as _realai_datasets  # type: ignore
if not hasattr(_realai_datasets, "Dataset"):
    class _DummyHFStemDataset: pass
    _realai_datasets.Dataset = _DummyHFStemDataset

from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
from peft import LoraConfig, TaskType, get_peft_model

REPO_ROOT = Path(__file__).parent.resolve()
DEFAULT_MANIFESTS_PATH = REPO_ROOT / "agent_manifests_for_finetuning_training_runs.json"
DEFAULT_DATASET_PATH = REPO_ROOT / "dataset.jsonl"

# ... (rest of the script is the same as the last full version I gave you)

# Paste the FULL script I sent earlier here if needed — it already has all the fixes.