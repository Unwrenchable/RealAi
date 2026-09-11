"""
Canonical training_data
=======================
Recovered from realai/training/build_datasets.py and training/build_datasets.py.

Re-exports recovered dataset builders. Does not start training on import.
"""
from __future__ import annotations

STATUS = "recovered"
CANONICAL_NAME = "training_data"
RECOVERED_FROM = "realai/training/build_datasets.py"

try:
    from realai.training.build_datasets import build_dataset_bundle  # noqa: F401
except Exception:
    def build_dataset_bundle(*args, **kwargs):  # type: ignore
        raise RuntimeError("build_dataset_bundle unavailable; recovered module failed to import")

try:
    from realai.training import (  # noqa: F401
        build_finetune_plan,
        evaluate_instruction_dataset,
        extract_agent_tool_data,
    )
except Exception:
    pass


def describe():
    return {
        "canonical": CANONICAL_NAME,
        "status": STATUS,
        "recovered_from": RECOVERED_FROM,
        "starts_training_on_import": False,
    }
