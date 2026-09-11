#!/usr/bin/env python3
"""
Craft-style training dispatch — walk learn/memory/train scripts → ingest → wire → optional LoRA.

  python scripts/dispatch_training.py
  python scripts/dispatch_training.py --train --preset qwen-coder-1.5b --max-steps 50
  python scripts/dispatch_training.py --train --device directml

Phases:
  1) walk_training_sources.py
  2) wire_training.py (ingest hooks + LoRA-ready JSONL)
  3) amd_stack_status.py (Vulkan chat + DirectML)
  4) optional train_lora_local.py
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "scan_results" / "TRAINING_DISPATCH.json"
REPORT_MD = ROOT / "scan_results" / "TRAINING_DISPATCH.md"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: List[str], timeout: int = 3600) -> Dict[str, Any]:
    print(f"[train-dispatch] RUN {' '.join(cmd)}", flush=True)
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        ok = completed.returncode == 0
        print(f"[train-dispatch] {'OK' if ok else 'FAIL'} rc={completed.returncode}", flush=True)
        if completed.stdout:
            for ln in completed.stdout.strip().splitlines()[-8:]:
                print(f"  out> {ln[:180]}", flush=True)
        if completed.stderr and not ok:
            for ln in completed.stderr.strip().splitlines()[-6:]:
                print(f"  err> {ln[:180]}", flush=True)
        return {
            "cmd": cmd,
            "ok": ok,
            "returncode": completed.returncode,
            "stdout_tail": (completed.stdout or "")[-2000:],
            "stderr_tail": (completed.stderr or "")[-1000:],
        }
    except subprocess.TimeoutExpired:
        return {"cmd": cmd, "ok": False, "error": f"timeout>{timeout}s"}
    except Exception as e:
        return {"cmd": cmd, "ok": False, "error": str(e)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Dispatch training ingest/wire/train pipeline")
    ap.add_argument("--train", action="store_true", help="Also start LoRA after wire")
    ap.add_argument("--preset", default="qwen-coder-1.5b")
    ap.add_argument("--device", default=os.environ.get("REALAI_TRAIN_DEVICE") or "directml")
    ap.add_argument("--max-steps", type=int, default=50)
    ap.add_argument("--skip-status", action="store_true")
    args = ap.parse_args()

    # Ensure DirectML DLL on PATH for AMD
    dml = os.environ.get("REALAI_DIRECTML_DIR") or r"C:\DirectML\runtime\x64"
    if Path(dml).is_dir():
        os.environ["PATH"] = dml + os.pathsep + os.environ.get("PATH", "")
        os.environ["REALAI_DIRECTML_DIR"] = dml

    py = sys.executable
    results: List[Dict[str, Any]] = []

    results.append(run([py, str(ROOT / "scripts" / "walk_training_sources.py")], timeout=600))
    results.append(
        run(
            [py, str(ROOT / "scripts" / "wire_training.py"), "--refresh-walk"],
            timeout=900,
        )
    )
    if not args.skip_status:
        results.append(run([py, str(ROOT / "scripts" / "amd_stack_status.py")], timeout=120))

    train_res = None
    if args.train:
        train_cmd = [
            py,
            "-u",
            str(ROOT / "scripts" / "train_lora_local.py"),
            "--preset",
            args.preset,
            "--device",
            args.device,
            "--max-steps",
            str(args.max_steps),
        ]
        train_res = run(train_cmd, timeout=7200)
        results.append(train_res)

    ok = all(r.get("ok") for r in results if r is not None)
    payload = {
        "at": utc(),
        "ok": ok,
        "train": bool(args.train),
        "preset": args.preset,
        "device": args.device,
        "results": results,
        "artifacts": {
            "walk": str(ROOT / "scan_results" / "TRAINING_SOURCES_WALK.md"),
            "wire": str(ROOT / "scan_results" / "TRAINING_WIRE.md"),
            "dataset": r"C:\models\checkpoints_lora\normalized_datasets\realai_lora_ready.jsonl",
        },
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = [
        f"# Training dispatch ({'TRAIN' if args.train else 'WIRE ONLY'})",
        "",
        f"- at: {payload['at']}",
        f"- ok: {ok}",
        f"- preset: {args.preset} device={args.device}",
        "",
        "## Phases",
    ]
    for r in results:
        cmd = " ".join(r.get("cmd") or [])
        lines.append(f"- {'OK' if r.get('ok') else 'FAIL'}: `{cmd}`")
    lines += [
        "",
        "## Artifacts",
        f"- walk: `{payload['artifacts']['walk']}`",
        f"- wire: `{payload['artifacts']['wire']}`",
        f"- dataset: `{payload['artifacts']['dataset']}`",
        "",
        "Craft: `/dispatch training` · `/dispatch training train` · `/train-walk`",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[train-dispatch] wrote {REPORT}")
    print(f"[train-dispatch] wrote {REPORT_MD}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
