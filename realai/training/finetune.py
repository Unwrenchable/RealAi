"""Fine-tune a base HF model on RealAI corpora; output merges under models/<id>/hf/."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from realai.model_assets import models_root


def build_finetune_plan(data_dir: Optional[str] = None, model_id: str = "realai-1.0-instruct") -> Dict[str, Any]:
    """Return the train/val paths and artifact directories for a fine-tune job."""
    dataset_dir = Path(data_dir) if data_dir else Path(__file__).resolve().parents[1] / "datasets" / "processed"
    train_path = dataset_dir / "train.jsonl"
    val_path = dataset_dir / "val.jsonl"
    hf_out = models_root() / model_id / "hf"
    return {
        "status": "ready",
        "model_id": model_id,
        "train_path": str(train_path),
        "val_path": str(val_path),
        "hf_output_dir": str(hf_out),
        "base_model": os.environ.get("REALAI_BASE_HF_MODEL", "Qwen/Qwen2.5-1.5B-Instruct"),
    }


def _load_messages_dataset(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        item = json.loads(line)
        if "messages" in item:
            rows.append(item)
        elif "instruction" in item and "output" in item:
            rows.append(
                {
                    "messages": [
                        {"role": "user", "content": item["instruction"]},
                        {"role": "assistant", "content": item["output"]},
                    ]
                }
            )
    return rows


def _format_chat_example(messages: List[Dict[str, str]]) -> str:
    parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        parts.append(f"<|{role}|>\n{content}")
    parts.append("<|assistant|>\n")
    return "\n".join(parts)


def run_finetune(
    *,
    data_dir: Optional[str] = None,
    model_id: str = "realai-1.0-instruct",
    max_steps: int = 50,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    plan = build_finetune_plan(data_dir=data_dir, model_id=model_id)
    train_rows = _load_messages_dataset(Path(plan["train_path"]))
    if not train_rows:
        return {**plan, "status": "no_data", "message": "Run build_datasets first."}

    # Guidance for users who want a different (or gated) base model
    if "Llama" in plan["base_model"] or "llama" in plan["base_model"]:
        print("[realai] Note: You are using a Llama base model. If you hit a gated repo error, either:")
        print("  - export REALAI_BASE_HF_MODEL=Qwen/Qwen2.5-1.5B-Instruct   (recommended public default)")
        print("  - or run: huggingface-cli login   (and accept the license on the HF model page)")

    try:
        from datasets import Dataset
        from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
    except ImportError as exc:
        return {
            **plan,
            "status": "missing_deps",
            "message": "Install training extras: pip install -r requirements-training.txt",
            "error": str(exc),
        }

    hf_dir = Path(output_dir) if output_dir else Path(plan["hf_output_dir"])
    hf_dir.mkdir(parents=True, exist_ok=True)

    base_model = plan["base_model"]
    texts = [_format_chat_example(row["messages"]) for row in train_rows]
    dataset = Dataset.from_dict({"text": texts})

    try:
        tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            base_model,
            trust_remote_code=True,
            device_map="auto" if os.environ.get("REALAI_TRAIN_DEVICE", "auto") == "auto" else None,
        )
    except Exception as exc:
        # Common case: gated repo (Llama, etc.) without HF login / token
        if "gated" in str(exc).lower() or "401" in str(exc) or "Unauthorized" in str(exc):
            return {
                **plan,
                "status": "gated_repo",
                "message": (
                    "The chosen base model is gated on Hugging Face.\n"
                    "Solutions:\n"
                    "  1. Set a public base model:  $env:REALAI_BASE_HF_MODEL = 'Qwen/Qwen2.5-1.5B-Instruct'\n"
                    "  2. Or log in: huggingface-cli login   (and accept the model license on HF website)\n"
                    "  3. Or set HF_TOKEN env var with a token that has access.\n"
                    f"Current base_model: {base_model}"
                ),
                "error": str(exc),
            }
        return {
            **plan,
            "status": "model_load_failed",
            "message": f"Failed to load base model {base_model}. Check internet / HF token / disk space.",
            "error": str(exc),
        }

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=2048)

    tokenized = dataset.map(tokenize, batched=True, remove_columns=["text"])

    args = TrainingArguments(
        output_dir=str(hf_dir / "checkpoints"),
        per_device_train_batch_size=int(os.environ.get("REALAI_TRAIN_BATCH", "1")),
        gradient_accumulation_steps=int(os.environ.get("REALAI_TRAIN_GRAD_ACCUM", "4")),
        max_steps=max_steps,
        learning_rate=float(os.environ.get("REALAI_TRAIN_LR", "2e-5")),
        logging_steps=5,
        save_steps=max_steps,
        report_to=[],
    )

    trainer = Trainer(model=model, args=args, train_dataset=tokenized)
    trainer.train()
    merged = hf_dir / "merged"
    model.save_pretrained(merged)
    tokenizer.save_pretrained(merged)

    manifest = {
        "model_id": model_id,
        "base_model": base_model,
        "train_examples": len(train_rows),
        "max_steps": max_steps,
        "merged_dir": str(merged),
    }
    (hf_dir / "finetune_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return {**plan, "status": "trained", "merged_dir": str(merged), "manifest": manifest}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fine-tune RealAI instruct weights (HF merge output)")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--model-id", default="realai-1.0-instruct")
    parser.add_argument("--max-steps", type=int, default=50)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--plan-only", action="store_true")
    return parser


def main(argv: Optional[list[str]] = None) -> Dict[str, Any]:
    args = build_parser().parse_args(argv)
    if args.plan_only:
        plan = build_finetune_plan(data_dir=args.data_dir, model_id=args.model_id)
        print(json.dumps(plan, indent=2))
        return plan
    result = run_finetune(
        data_dir=args.data_dir,
        model_id=args.model_id,
        max_steps=args.max_steps,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()