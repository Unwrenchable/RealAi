"""Fine-tune planning for RealAI — prefers Phase-2 training/data gold."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

# realai/training/ -> parents[1] is package root realai/, parents[2] is repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DATA = _REPO_ROOT / "training" / "data"


def build_finetune_plan(data_dir: Optional[str] = None) -> Dict[str, Any]:
    """Return train paths for local gold datasets (jsonl + agent manifests).

    Prefers:
      training/data/realai_finetune_dataset.jsonl
      training/data/agent_manifests_for_finetuning.json

    Falls back to datasets/processed/train.jsonl layout if present.
    """
    dataset_dir = Path(data_dir) if data_dir else _DEFAULT_DATA
    gold = dataset_dir / "realai_finetune_dataset.jsonl"
    manifests = dataset_dir / "agent_manifests_for_finetuning.json"
    legacy_train = dataset_dir / "train.jsonl"
    legacy_val = dataset_dir / "val.jsonl"
    # older stub path under package
    pkg_processed = Path(__file__).resolve().parents[1] / "datasets" / "processed"

    train_path = gold if gold.is_file() else (
        legacy_train if legacy_train.is_file() else pkg_processed / "train.jsonl"
    )
    val_path = legacy_val if legacy_val.is_file() else pkg_processed / "val.jsonl"

    lines = 0
    if Path(train_path).is_file() and str(train_path).endswith(".jsonl"):
        try:
            with open(train_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = sum(1 for _ in f)
        except OSError:
            lines = -1

    return {
        "status": "ready" if Path(train_path).is_file() else "missing_dataset",
        "train_path": str(train_path),
        "val_path": str(val_path) if Path(val_path).is_file() else None,
        "manifests_path": str(manifests) if manifests.is_file() else None,
        "train_lines": lines,
        "data_dir": str(dataset_dir),
        "note": "Phase-2 gold under training/data; use with self_improvement when REALAI_SELF_IMPROVE=true",
    }


def main() -> Dict[str, Any]:
    plan = build_finetune_plan()
    print("[realai] Fine-tune plan: {0}".format(plan))
    return plan


if __name__ == "__main__":
    main()
