#!/usr/bin/env python3
"""
Discover RealAI + C:\\models training assets, build a LoRA-ready JSONL,
and write wiring maps under scan_results/ + C:\\models.

  python scripts/wire_training.py
  python scripts/wire_training.py --start-train --max-steps 50
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

REALAI = Path(__file__).resolve().parents[1]
MODELS = Path(os.environ.get("REALAI_MODELS_DIR") or r"C:\models")
CKPT = MODELS / "checkpoints_lora"
OUT_DATA = CKPT / "normalized_datasets" / "realai_lora_ready.jsonl"
REPORT = REALAI / "scan_results" / "TRAINING_WIRE.json"
REPORT_MD = REALAI / "scan_results" / "TRAINING_WIRE.md"

# Known good corpora inside RealAI (skip the misnamed 4GB config dumps)
SOURCE_JSONL = [
    REALAI / "realai" / "plugins" / "dataset.jsonl",  # text, ~8k
    REALAI / "training" / "data" / "realai_finetune_dataset.jsonl",
    REALAI / "training" / "data" / "ability_surface.jsonl",
    REALAI / "modules" / "training" / "datasets" / "realai_finetune_dataset.jsonl",
    REALAI / "modules" / "training" / "datasets" / "ability_surface.jsonl",
    REALAI / "imports" / "external" / "grok_export_realai" / "datasets" / "processed" / "train.jsonl",
    REALAI / "imports" / "external" / "grok_export_realai" / "datasets" / "processed" / "instructions.jsonl",
    REALAI / "imports" / "external" / "grok_export_realai" / "datasets" / "processed" / "self_builder_sessions.jsonl",
]

MANIFESTS = [
    REALAI / "training" / "data" / "agent_manifests_for_finetuning.json",
    REALAI / "agents" / "agentx" / "agent_manifests_for_finetuning.json",
]

TRAINERS = [
    REALAI / "scripts" / "train_lora_local.py",
    REALAI / "core" / "training" / "train_qwen_lora_directml.py",
    REALAI / "core" / "training" / "train_from_agent_manifests.py",
    REALAI / "training" / "unsloth_train.py",
    REALAI / "realai" / "training" / "pipeline.py",
    REALAI / "realai" / "training" / "finetune.py",
]


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def row_to_text(obj: Dict[str, Any]) -> Optional[str]:
    if not isinstance(obj, dict):
        return None
    if isinstance(obj.get("text"), str) and obj["text"].strip():
        return obj["text"].strip()
    if isinstance(obj.get("instruction"), str) and isinstance(obj.get("response"), str):
        return f"### Instruction:\n{obj['instruction'].strip()}\n\n### Response:\n{obj['response'].strip()}"
    msgs = obj.get("messages")
    if isinstance(msgs, list) and msgs:
        parts = []
        for m in msgs:
            if not isinstance(m, dict):
                continue
            role = m.get("role") or "user"
            content = (m.get("content") or "").strip()
            if content:
                parts.append(f"<|{role}|>\n{content}")
        if parts:
            return "\n".join(parts)
    # self-builder session
    task = obj.get("task")
    if isinstance(task, str) and task.strip():
        result = obj.get("result") or {}
        summary = ""
        if isinstance(result, dict):
            summary = str(result.get("summary") or "")
        assistant = summary or json.dumps(result)[:4000]
        return f"<|user|>\n{task.strip()}\n<|assistant|>\n{assistant}"
    return None


def iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj


def build_ready_dataset(sources: List[Path], out: Path, max_rows: int = 20000) -> Dict[str, Any]:
    out.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    kept = 0
    per_source: Dict[str, int] = {}
    with out.open("w", encoding="utf-8") as w:
        for src in sources:
            if not src.is_file():
                continue
            n = 0
            for obj in iter_jsonl(src):
                text = row_to_text(obj)
                if not text:
                    continue
                key = text[:400]
                if key in seen:
                    continue
                seen.add(key)
                w.write(json.dumps({"text": text, "source": str(src)}, ensure_ascii=False) + "\n")
                kept += 1
                n += 1
                if kept >= max_rows:
                    per_source[str(src)] = per_source.get(str(src), 0) + n
                    return {"rows": kept, "path": str(out), "per_source": per_source, "truncated": True}
            if n:
                per_source[str(src)] = n
    return {"rows": kept, "path": str(out), "per_source": per_source, "truncated": False}


def discover_lora_adapters(ckpt: Path) -> List[Dict[str, Any]]:
    found = []
    if not ckpt.is_dir():
        return found
    for cfg in ckpt.rglob("adapter_config.json"):
        try:
            rel = str(cfg.parent.relative_to(ckpt)).replace("\\", "/")
        except ValueError:
            rel = str(cfg.parent)
        weights = cfg.parent / "adapter_model.safetensors"
        found.append(
            {
                "id": rel.replace("/", "-") or cfg.parent.name,
                "path": str(cfg.parent),
                "has_weights": weights.is_file(),
                "bytes": weights.stat().st_size if weights.is_file() else 0,
            }
        )
    found.sort(key=lambda x: -x["bytes"])
    return found


def write_peft_lists(adapters: List[Dict[str, Any]]) -> List[str]:
    lines = [a["path"] for a in adapters if a.get("has_weights")]
    targets = [
        MODELS / "peft_merge_list.txt",
        CKPT / "peft_merge_list.txt",
    ]
    wrote = []
    for t in targets:
        try:
            t.parent.mkdir(parents=True, exist_ok=True)
            t.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
            wrote.append(str(t))
        except OSError:
            pass
    return wrote


def load_walk_sources(max_extra: int = 40) -> Dict[str, Any]:
    """Merge usable JSONL + extract scripts from training walk (like craft dispatch discovery)."""
    walk_path = REALAI / "scan_results" / "TRAINING_SOURCES_WALK.json"
    info: Dict[str, Any] = {"walk_path": str(walk_path), "extra_jsonl": [], "extractors": [], "memory": []}
    if not walk_path.is_file():
        return info
    try:
        walk = json.loads(walk_path.read_text(encoding="utf-8"))
    except Exception:
        return info
    needs = walk.get("model_needs") or {}
    for rel in (needs.get("jsonl_corpora") or [])[:max_extra]:
        p = REALAI / rel
        if p.is_file() and p.stat().st_size < 50_000_000:
            info["extra_jsonl"].append(p)
    for rel in (needs.get("extract_scripts") or [])[:20]:
        info["extractors"].append(rel)
    for rel in (needs.get("memory_modules") or [])[:30]:
        info["memory"].append(rel)
    info["counts"] = walk.get("counts")
    return info


def run_ingest_hooks() -> Dict[str, Any]:
    """Run safe extractors so learning/memory feeds become JSONL for models."""
    results: Dict[str, Any] = {"ok": True, "steps": []}
    # 1) ability catalog training samples
    try:
        from realai.ability_catalog import emit_training_samples

        r = emit_training_samples()
        results["steps"].append({"name": "emit_training_samples", "ok": True, "result": r})
        print(f"[wire-training] emit_training_samples → {r}")
    except Exception as e:
        results["steps"].append({"name": "emit_training_samples", "ok": False, "error": str(e)})
        print(f"[wire-training] emit_training_samples skipped: {e}")

    # 2) realai.training extract → instructions.jsonl
    try:
        from realai.training.extract_from_agent_tools import extract_all_training_sources

        out_dir = REALAI / "datasets" / "processed"
        r = extract_all_training_sources(out_dir)
        results["steps"].append({"name": "extract_all_training_sources", "ok": True, "result": r})
        print(f"[wire-training] extract_all_training_sources → {r}")
    except Exception as e:
        results["steps"].append({"name": "extract_all_training_sources", "ok": False, "error": str(e)})
        print(f"[wire-training] extract skipped: {e}")

    # 3) agent_tools extractor if present
    ext = REALAI / "agent_tools" / "extract_from_agent_tools.py"
    if ext.is_file():
        try:
            completed = subprocess.run(
                [sys.executable, str(ext)],
                cwd=str(REALAI),
                capture_output=True,
                text=True,
                timeout=300,
                encoding="utf-8",
                errors="replace",
            )
            results["steps"].append(
                {
                    "name": "agent_tools.extract_from_agent_tools",
                    "ok": completed.returncode == 0,
                    "returncode": completed.returncode,
                    "stdout_tail": (completed.stdout or "")[-500:],
                }
            )
        except Exception as e:
            results["steps"].append({"name": "agent_tools.extract_from_agent_tools", "ok": False, "error": str(e)})
    return results


def catalog() -> Dict[str, Any]:
    walk_info = load_walk_sources()
    extra_paths = [Path(p) for p in (walk_info.get("extra_jsonl") or [])]
    # JSON-safe walk summary (Path objects → strings)
    walk_info_json = {
        **{k: v for k, v in walk_info.items() if k != "extra_jsonl"},
        "extra_jsonl": [str(p) for p in extra_paths],
    }
    sources_present = []
    seen = set()
    for p in list(SOURCE_JSONL) + extra_paths:
        p = Path(p)
        if not p.is_file():
            continue
        key = str(p.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        sources_present.append({"path": str(p), "bytes": p.stat().st_size})
    # also pick up freshly emitted ability_surface / instructions
    for extra in (
        REALAI / "training" / "data" / "ability_surface.jsonl",
        REALAI / "datasets" / "processed" / "instructions.jsonl",
        REALAI / "datasets" / "processed" / "train.jsonl",
        REALAI / "realai" / "datasets" / "processed" / "instructions.jsonl",
    ):
        if extra.is_file():
            key = str(extra.resolve()).lower()
            if key not in seen:
                seen.add(key)
                sources_present.append({"path": str(extra), "bytes": extra.stat().st_size})

    trainers = [{"path": str(p), "exists": p.is_file()} for p in TRAINERS]
    trainers.append({"path": str(REALAI / "scripts" / "walk_training_sources.py"), "exists": (REALAI / "scripts" / "walk_training_sources.py").is_file()})
    trainers.append({"path": str(REALAI / "scripts" / "dispatch_training.py"), "exists": (REALAI / "scripts" / "dispatch_training.py").is_file()})
    manifests = [{"path": str(p), "exists": p.is_file(), "bytes": p.stat().st_size if p.is_file() else 0} for p in MANIFESTS]
    adapters = discover_lora_adapters(CKPT)
    return {
        "at": utc(),
        "realai": str(REALAI),
        "models_dir": str(MODELS),
        "checkpoints_lora": str(CKPT),
        "sources": sources_present,
        "trainers": trainers,
        "manifests": manifests,
        "walk": walk_info_json,
        "lora_adapters": adapters[:80],
        "lora_adapter_count": len(adapters),
        "notes": [
            "Training walk (scripts/walk_training_sources.py) discovers learn/memory/finetune scripts like craft dispatch.",
            "wire_training merges those JSONL corpora + runs extract/ingest hooks before building LoRA-ready data.",
            "C:\\models\\normalized_datasets\\train_combined.jsonl is a misnamed multi-JSON config dump (~4GB) — NOT used.",
            "INFERENCE (chat/GGUF): Vulkan llama-server — REALAI_VULKAN_BASE=http://127.0.0.1:8080",
            "TRAINING (LoRA/PEFT): scripts/train_lora_local.py — DirectML (AMD) → CUDA → CPU.",
            "Craft: /dispatch training  or  /train-walk  /train wire",
        ],
    }


def _directml_ok() -> bool:
    try:
        import importlib

        importlib.import_module("torch_directml")
        import torch_directml  # noqa: F401

        return True
    except Exception:
        return False


def start_train(dataset: Path, max_steps: int, adapter_subdir: str) -> Dict[str, Any]:
    # Prefer portable local trainer; DirectML path is optional (often broken DLL)
    local = REALAI / "scripts" / "train_lora_local.py"
    dml = REALAI / "core" / "training" / "train_qwen_lora_directml.py"
    if local.is_file():
        trainer = local
        cmd = [
            sys.executable,
            "-u",
            str(trainer),
            "--dataset",
            str(dataset),
            "--output-dir",
            str(CKPT),
            "--adapter-subdir",
            adapter_subdir,
            "--max-steps",
            str(max_steps),
        ]
        backend = "cuda_or_cpu"
    elif dml.is_file() and _directml_ok():
        trainer = dml
        cmd = [sys.executable, "-u", str(trainer)]
        backend = "directml"
    else:
        return {
            "ok": False,
            "error": "no usable trainer (train_lora_local.py missing; DirectML unavailable)",
        }

    env = os.environ.copy()
    env["TRAIN_MODEL_NAME"] = env.get("TRAIN_MODEL_NAME") or "Qwen/Qwen2.5-1.5B-Instruct"
    env["TRAIN_DATASET_PATH"] = str(dataset)
    env["TRAIN_OUTPUT_DIR"] = str(CKPT)
    env["TRAIN_ADAPTER_SUBDIR"] = adapter_subdir
    env["TRAIN_MAX_STEPS"] = str(max_steps)
    env["TRAIN_BATCH_SIZE"] = env.get("TRAIN_BATCH_SIZE") or "1"
    env["TRAIN_MAX_LENGTH"] = env.get("TRAIN_MAX_LENGTH") or "256"
    env["TRAIN_LORA_R"] = env.get("TRAIN_LORA_R") or "16"
    env["PYTHONUNBUFFERED"] = "1"
    log_dir = REALAI / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    out_log = log_dir / "lora_train.out.log"
    err_log = log_dir / "lora_train.err.log"
    print(f"[wire-training] starting LoRA ({backend}) steps={max_steps} dataset={dataset}")
    print(f"[wire-training] output adapter → {CKPT / adapter_subdir}")
    with out_log.open("w", encoding="utf-8") as out, err_log.open("w", encoding="utf-8") as err:
        proc = subprocess.Popen(
            cmd,
            cwd=str(REALAI),
            env=env,
            stdout=out,
            stderr=err,
        )
    return {
        "ok": True,
        "pid": proc.pid,
        "backend": backend,
        "trainer": str(trainer),
        "dataset": str(dataset),
        "adapter_dir": str(CKPT / adapter_subdir),
        "max_steps": max_steps,
        "logs": {"out": str(out_log), "err": str(err_log)},
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Wire RealAI training assets to C:\\models LoRA pipeline")
    ap.add_argument("--max-rows", type=int, default=20000)
    ap.add_argument("--start-train", action="store_true")
    ap.add_argument("--max-steps", type=int, default=50)
    ap.add_argument("--adapter-subdir", default="qwen2.5-1.5b-lora-realai")
    ap.add_argument("--wait", action="store_true", help="Wait for training process to finish")
    ap.add_argument("--skip-ingest", action="store_true", help="Skip extract/memory ingest hooks")
    ap.add_argument("--refresh-walk", action="store_true", help="Re-run walk_training_sources first")
    args = ap.parse_args(argv)

    if str(REALAI) not in sys.path:
        sys.path.insert(0, str(REALAI))

    if args.refresh_walk or not (REALAI / "scan_results" / "TRAINING_SOURCES_WALK.json").is_file():
        print("[wire-training] running walk_training_sources.py …")
        subprocess.run(
            [sys.executable, str(REALAI / "scripts" / "walk_training_sources.py")],
            cwd=str(REALAI),
            check=False,
        )

    ingest = None
    if not args.skip_ingest:
        print("[wire-training] ingest hooks (ability samples / extract / agent_tools) …")
        ingest = run_ingest_hooks()

    cat = catalog()
    cat["ingest"] = ingest
    print(f"[wire-training] sources={len(cat['sources'])} adapters={cat['lora_adapter_count']}")
    for s in cat["sources"][:25]:
        print(f"  source> {s['path']} ({s['bytes']}B)")
    if len(cat["sources"]) > 25:
        print(f"  ... +{len(cat['sources']) - 25} more")

    built = build_ready_dataset(
        [Path(s["path"]) for s in cat["sources"]],
        OUT_DATA,
        max_rows=int(args.max_rows),
    )
    print(f"[wire-training] ready dataset rows={built['rows']} → {built['path']}")

    peft_wrote = write_peft_lists(cat["lora_adapters"])
    print(f"[wire-training] peft lists → {peft_wrote}")

    # Mirror curated RealAI training data under C:\models for convenience
    mirror_dir = CKPT / "realai_training_data"
    mirror_dir.mkdir(parents=True, exist_ok=True)
    mirrored = []
    for src in [
        REALAI / "training" / "data" / "realai_finetune_dataset.jsonl",
        REALAI / "training" / "data" / "ability_surface.jsonl",
        REALAI / "training" / "data" / "agent_manifests_for_finetuning.json",
        OUT_DATA,
    ]:
        if src.is_file():
            dest = mirror_dir / src.name
            dest.write_bytes(src.read_bytes())
            mirrored.append(str(dest))

    train_info = None
    if args.start_train:
        if built["rows"] <= 0:
            print("[wire-training] no rows — cannot start train", file=sys.stderr)
            return 1
        train_info = start_train(OUT_DATA, int(args.max_steps), args.adapter_subdir)
        print(f"[wire-training] train launched pid={train_info.get('pid')} logs={train_info.get('logs')}")
        if args.wait and train_info.get("pid"):
            import time

            # poll until process exits
            try:
                import psutil  # type: ignore

                proc = psutil.Process(train_info["pid"])
                proc.wait()
                train_info["wait_exit"] = proc.status() if False else "done"
            except Exception:
                # fallback: wait on handle if still our child — Popen not kept; just sleep poll via tasklist
                while True:
                    r = subprocess.run(
                        ["tasklist", "/FI", f"PID eq {train_info['pid']}"],
                        capture_output=True,
                        text=True,
                    )
                    if str(train_info["pid"]) not in (r.stdout or ""):
                        break
                    time.sleep(5)
                train_info["wait_exit"] = "exited"

    payload = {
        **cat,
        "ready_dataset": built,
        "peft_lists": peft_wrote,
        "mirrored": mirrored,
        "train": train_info,
        "how_to": {
            "wire_only": "python scripts/wire_training.py",
            "start_lora": "python scripts/wire_training.py --start-train --max-steps 50",
            "pipeline_status": "python -m realai.training.pipeline --stage status",
            "manual_env": {
                "TRAIN_MODEL_NAME": "Qwen/Qwen2.5-1.5B-Instruct",
                "TRAIN_DATASET_PATH": str(OUT_DATA),
                "TRAIN_OUTPUT_DIR": str(CKPT),
                "TRAIN_ADAPTER_SUBDIR": args.adapter_subdir,
                "TRAIN_MAX_STEPS": str(args.max_steps),
            },
        },
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Training wire map",
        "",
        f"- at: {payload['at']}",
        f"- models: `{MODELS}`",
        f"- ready dataset: `{built['path']}` rows={built['rows']}",
        f"- lora adapters found: {cat['lora_adapter_count']}",
        "",
        "## Sources wired",
    ]
    for s in cat["sources"]:
        lines.append(f"- `{s['path']}` ({s['bytes']} bytes)")
    lines += ["", "## Trainers", ""]
    for t in cat["trainers"]:
        lines.append(f"- {'OK' if t['exists'] else 'MISSING'} `{t['path']}`")
    lines += ["", "## Existing LoRA adapters (top)", ""]
    for a in cat["lora_adapters"][:15]:
        lines.append(f"- `{a['id']}` weights={a['has_weights']} bytes={a['bytes']}")
    lines += [
        "",
        "## Start LoRA",
        "",
        "```powershell",
        "python scripts/wire_training.py --start-train --max-steps 50",
        "```",
        "",
        f"Adapter output: `{CKPT / args.adapter_subdir}`",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[wire-training] wrote {REPORT}")
    print(f"[wire-training] wrote {REPORT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
