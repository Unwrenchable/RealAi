"""
The solid, complete local self-improvement loop.

This is the command that makes "RealAI builds itself locally" actually true.

    realai-loop
    realai-loop --iterations 3
    realai-loop --task "your concrete improvement here"

It:
- Picks the best available local coding model (qwen-coder-7b preferred when ready)
- Runs a strict ReAct-style agent using only GGUF inference + 5 safe repo tools
- Captures every trace for future training
- Ingests into clean JSONL and rebuilds train/val splits
- Leaves you with clear next steps (finetune / export) when you have cycles

All without a single external API key.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .model_assets import repo_root
from .sdk.python.realai_client import RealAIClient
from .self_builder import SelfBuilder, select_builder_model as _select  # internal, we have a better picker below


def check_server(api_url: str) -> Dict[str, Any]:
    client = RealAIClient(api_url=api_url, timeout=15)
    health = client.health()
    models = client.models()
    ready = [
        m.get("id")
        for m in (models.get("data") or [])
        if m.get("weights_ready") is not False and m.get("type") == "chat"
    ]
    return {"health": health, "chat_models_ready": ready}


def ingest_self_builder_sessions() -> Dict[str, Any]:
    from .training.extract_from_agent_tools import extract_all_training_sources

    return extract_all_training_sources()


def _best_local_coder(api_url: str) -> str:
    try:
        client = RealAIClient(api_url=api_url, timeout=10)
        data = client.models().get("data") or []
        for mid in ("qwen-coder-7b", "realai-1.0-instruct", "realai-1.0"):
            for m in data:
                if m.get("id") == mid and m.get("weights_ready") is not False:
                    return mid
    except Exception:
        pass
    return "realai-1.0-instruct"


def run_self_build(
    task: str, api_url: str, model: Optional[str], max_steps: int, auto_confirm: bool = True
) -> Dict[str, Any]:
    m = model or _best_local_coder(api_url)
    builder = SelfBuilder(api_url=api_url, model=m, max_steps=int(max_steps), auto_confirm=auto_confirm)
    return builder.run(task)


def default_autonomy_task() -> str:
    """A task that the current 7B model can realistically complete while still providing training value."""
    return (
        "Use run_terminal_command to run 'python -m unittest tests.test_self_builder tests.test_agent_protocol tests.test_extract_sessions -q'. "
        "When the output shows all tests passing and exit_code 0, reply with DONE. "
        "Keep the command simple and do not read large files unless necessary."
    )


def close_the_loop(
    *,
    api_url: str,
    task: Optional[str] = None,
    model: Optional[str] = None,
    max_steps: int = 20,
    iterations: int = 1,
    skip_build: bool = False,
    auto_confirm: bool = True,
) -> Dict[str, Any]:
    report: Dict[str, Any] = {"api_url": api_url, "phases": {}}

    report["phases"]["server"] = check_server(api_url)
    if not report["phases"]["server"].get("chat_models_ready"):
        report["status"] = "blocked"
        report["message"] = "Start server: python -m realai.server.app"
        return report

    if not skip_build:
        build_task = task or default_autonomy_task()
        for _ in range(max(1, int(iterations))):
            b = run_self_build(build_task, api_url, model, max_steps, auto_confirm=auto_confirm)
            if "iterations" not in report:
                report["iterations"] = []
            report["iterations"].append(b)

    report["phases"]["ingest"] = ingest_self_builder_sessions()
    from .training.build_datasets import build_dataset_bundle

    report["phases"]["datasets"] = build_dataset_bundle()
    from .training.pipeline import run_stage

    report["phases"]["weights"] = run_stage("status")

    last = (report.get("iterations") or [{}])[-1] if not skip_build else {}
    if skip_build:
        report["status"] = "closed"
    elif last.get("status") == "done":
        report["status"] = "closed"
    elif last.get("status") in (None, "max_steps"):
        report["status"] = "partial"
        if last.get("status") == "max_steps":
            report["message"] = "Agent hit max_steps on last iteration; sessions still captured for training."
    else:
        report["status"] = "partial"

    report["next"] = {
        "keep going": "realai-loop --iterations 2   (or python -m realai.closed_loop --iterations 2)",
        "train on the traces": "pip install -r requirements-training.txt && python -m realai.training.pipeline --stage finetune",
        "export new weights": "python -m realai.training.pipeline --stage export",
        "switch to your own checkpoint": "Stop the server first (Ctrl+C), then: python -m realai.training.bootstrap_weights",
    }
    return report


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="realai-loop — the one command that lets RealAI build itself locally."
    )
    p.add_argument("--api-url", default=os.environ.get("REALAI_API_URL", "http://127.0.0.1:8000"))
    p.add_argument("--task", default=None, help="Concrete improvement task (a good default is used otherwise)")
    p.add_argument("--model", default=None)
    p.add_argument("--max-steps", type=int, default=20)
    p.add_argument("--iterations", type=int, default=1, help="Number of autonomous improvement rounds")
    p.add_argument("--check-only", action="store_true")
    p.add_argument("--ingest-only", action="store_true")
    p.add_argument("--no-auto-confirm", action="store_true", help="Human approval for every edit/run (safer)")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.check_only:
        print(json.dumps(check_server(args.api_url), indent=2))
        return 0
    if args.ingest_only:
        print(json.dumps(ingest_self_builder_sessions(), indent=2))
        return 0

    result = close_the_loop(
        api_url=args.api_url,
        task=args.task,
        model=args.model,
        max_steps=args.max_steps,
        iterations=args.iterations,
        auto_confirm=not args.no_auto_confirm,
    )
    print(json.dumps(result, indent=2, default=str))

    if result.get("status") == "closed":
        print("\n[realai] Success. It just worked on itself with zero external APIs.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())