"""End-to-end native model pipeline: data → fine-tune → GGUF → eval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from realai.model_assets import list_realai_weight_status

from .build_datasets import build_dataset_bundle
from .eval import evaluate_instruction_dataset, evaluate_native_server
from .export_gguf import export_from_hf, publish_gguf
from .finetune import build_finetune_plan, run_finetune


def run_stage(stage: str, **kwargs) -> Dict[str, Any]:
    if stage == "datasets":
        return build_dataset_bundle(kwargs.get("data_dir"))
    if stage == "plan":
        return build_finetune_plan(kwargs.get("data_dir"), kwargs.get("model_id", "realai-1.0-instruct"))
    if stage == "finetune":
        return run_finetune(
            data_dir=kwargs.get("data_dir"),
            model_id=kwargs.get("model_id", "realai-1.0-instruct"),
            max_steps=int(kwargs.get("max_steps", 50)),
        )
    if stage == "export":
        model_id = kwargs.get("model_id", "realai-1.0-instruct")
        hf_dir = kwargs.get("hf_dir")
        gguf = kwargs.get("gguf")

        if gguf:
            return publish_gguf(
                Path(gguf),
                model_id,
                quant_label=kwargs.get("quant", "Q4_K_M"),
                copy_to=kwargs.get("copy_to") or ["realai-1.0"],
            )

        # If user explicitly gave hf-dir or the merged dir from a previous finetune exists, use HF path
        if hf_dir:
            return export_from_hf(
                Path(hf_dir),
                model_id,
                quant=kwargs.get("quant", "Q4_K_M"),
                copy_to=kwargs.get("copy_to") or ["realai-1.0"],
            )

        plan = build_finetune_plan(model_id=model_id)
        auto_hf = Path(plan["hf_output_dir"]) / "merged"
        if auto_hf.exists():
            return export_from_hf(
                auto_hf,
                model_id,
                quant=kwargs.get("quant", "Q4_K_M"),
                copy_to=kwargs.get("copy_to") or ["realai-1.0"],
            )

        # No HF checkpoint. Fall back to publishing an existing GGUF (bootstrap path).
        # Try the common dev reference GGUF first, then any .gguf under models/
        from .bootstrap_weights import discover_local_gguf
        candidates = discover_local_gguf()
        if candidates:
            # Prefer the Llama dev one if present, else the first one
            chosen = None
            for c in candidates:
                if "Llama" in c.name or "llama" in c.name:
                    chosen = c
                    break
            if not chosen:
                chosen = candidates[0]
            return publish_gguf(
                chosen,
                model_id,
                quant_label=kwargs.get("quant", "Q4_K_M"),
                copy_to=kwargs.get("copy_to") or ["realai-1.0"],
            )

        # Nothing available — give clear guidance
        raise FileNotFoundError(
            "No fine-tuned HF model and no existing GGUF found for export.\n"
            "Options:\n"
            "  1. Run finetune first:  python -m realai.training.pipeline --stage finetune\n"
            "  2. Brand an existing GGUF (recommended for bootstrap):  python -m realai.training.bootstrap_weights\n"
            "  3. Or pass an explicit GGUF:  python -m realai.training.pipeline --stage export --gguf path/to/your.gguf\n"
            f"Expected HF dir (after finetune): {auto_hf}\n"
            "Existing GGUFs discovered under models/: " + (", ".join(str(c) for c in candidates) if candidates else "none")
        )
    if stage == "eval":
        out: Dict[str, Any] = {"dataset": evaluate_instruction_dataset()}
        if kwargs.get("server"):
            out["server"] = evaluate_native_server(
                kwargs.get("server", "http://127.0.0.1:8000"),
                kwargs.get("model_id", "realai-1.0-instruct"),
            )
        out["weights"] = list_realai_weight_status()
        return out
    if stage == "status":
        return {"weights": list_realai_weight_status()}
    if stage == "ingest":
        from .extract_from_agent_tools import extract_all_training_sources

        return extract_all_training_sources(kwargs.get("data_dir"))
    if stage == "bootstrap":
        from .bootstrap_weights import bootstrap_native_weights

        return bootstrap_native_weights(
            model_id=kwargs.get("model_id", "realai-1.0-instruct"),
            source=kwargs.get("gguf"),
        )
    raise ValueError(f"Unknown stage: {stage}")


def run_all(model_id: str = "realai-1.0-instruct", max_steps: int = 50, server: Optional[str] = None) -> Dict[str, Any]:
    report: Dict[str, Any] = {"stages": {}}
    for stage in ("datasets", "finetune", "export", "eval"):
        try:
            report["stages"][stage] = run_stage(
                stage,
                model_id=model_id,
                max_steps=max_steps,
                server=server or "http://127.0.0.1:8000",
            )
        except Exception as exc:
            report["stages"][stage] = {"status": "error", "error": str(exc)}
            report["stopped_at"] = stage
            break
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RealAI native model training pipeline")
    parser.add_argument(
        "--stage",
        choices=["datasets", "plan", "finetune", "export", "eval", "status", "bootstrap", "ingest", "all"],
        default="status",
    )
    parser.add_argument("--model-id", default="realai-1.0-instruct")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--max-steps", type=int, default=50)
    parser.add_argument("--hf-dir", default=None)
    parser.add_argument("--gguf", default=None, help="Skip HF; publish an existing GGUF file")
    parser.add_argument("--quant", default="Q4_K_M")
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    return parser


def main(argv: Optional[List[str]] = None) -> Dict[str, Any]:
    args = build_parser().parse_args(argv)
    if args.stage == "all":
        result = run_all(model_id=args.model_id, max_steps=args.max_steps, server=args.server)
    else:
        result = run_stage(
            args.stage,
            data_dir=args.data_dir,
            model_id=args.model_id,
            max_steps=args.max_steps,
            hf_dir=args.hf_dir,
            gguf=args.gguf,
            quant=args.quant,
            server=args.server,
        )
    print(json.dumps(result, indent=2, default=str))
    return result


if __name__ == "__main__":
    main()