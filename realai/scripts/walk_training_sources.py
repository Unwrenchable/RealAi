#!/usr/bin/env python3
"""
Training-oriented walk — find scripts/data for learn / memory / finetune / LoRA.

Like walk_root, but classified for model training needs:
  extract | dataset | trainer | memory | self_improve | manifest | other

  python scripts/walk_training_sources.py
  python scripts/walk_training_sources.py --deepen

Writes:
  scan_results/TRAINING_SOURCES_WALK.json
  scan_results/TRAINING_SOURCES_WALK.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "scan_results" / "TRAINING_SOURCES_WALK.json"
OUT_MD = ROOT / "scan_results" / "TRAINING_SOURCES_WALK.md"

SKIP_DIRS = {
    "node_modules", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    "dist", "build", ".next", "models", "checkpoints_lora", ".mypy_cache",
    ".ruff_cache", "site-packages",
}
# Still scan imports/external lightly; skip bulk recovered dumps
SKIP_TREE = ("recovered/", "temp_repos/", "realai_historical")

ROLE_RULES = [
    ("extract", re.compile(r"extract_from_agent|emit_training|ingest|build_dataset", re.I)),
    ("trainer", re.compile(r"train_lora|train_qwen|finetune|unsloth_train|training_pipeline|train_from_agent", re.I)),
    ("pipeline", re.compile(r"pipeline\.py|wire_training|dispatch_training|bootstrap_weights|export_gguf", re.I)),
    ("dataset", re.compile(r"dataset|jsonl|manifests_for_finetune|ability_surface|normalized", re.I)),
    ("memory", re.compile(r"memory|aura_memory|episodic|semantic|dream_memory|memory_store|summarizer", re.I)),
    ("self_improve", re.compile(r"self_improve|self_builder|closed_loop|self_heal|deepen", re.I)),
    ("manifest", re.compile(r"agent_manifest|finetuning\.json", re.I)),
]

RUNNABLE_HINT = re.compile(
    r'if\s+__name__\s*==\s*[\'"]__main__[\'"]|argparse|def main\s*\(',
    re.I,
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify(rel: str, name: str) -> str:
    blob = f"{rel} {name}"
    for role, rx in ROLE_RULES:
        if rx.search(blob):
            return role
    return "other"


def should_skip(rel: str) -> bool:
    low = rel.replace("\\", "/").lower()
    return any(m in low for m in SKIP_TREE)


def walk(deepen: bool = False) -> Dict[str, Any]:
    scripts: List[Dict[str, Any]] = []
    jsonl_files: List[Dict[str, Any]] = []
    manifests: List[Dict[str, Any]] = []
    memory_modules: List[Dict[str, Any]] = []

    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        try:
            rel = str(p.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            continue
        if should_skip(rel) and not deepen:
            continue

        suf = p.suffix.lower()
        name = p.name
        role = classify(rel, name)

        if suf == ".py":
            # keep if role interesting or path under training/memory trees
            keep = role != "other" or any(
                x in rel.lower()
                for x in (
                    "/training/",
                    "\\training\\",
                    "/memory/",
                    "self_improve",
                    "finetune",
                    "lora",
                    "dataset",
                )
            )
            if not keep:
                continue
            runnable = False
            try:
                head = p.read_text(encoding="utf-8", errors="replace")[:8000]
                runnable = bool(RUNNABLE_HINT.search(head))
            except OSError:
                head = ""
            entry = {
                "rel": rel,
                "name": name,
                "role": role if role != "other" else classify(rel + " " + head[:200], name),
                "runnable": runnable,
                "bytes": p.stat().st_size,
                "depth": rel.count("/"),
            }
            if "memory" in rel.lower() or entry["role"] == "memory":
                memory_modules.append(entry)
            scripts.append(entry)

        elif suf == ".jsonl":
            # skip known junk giant config dumps
            try:
                sz = p.stat().st_size
            except OSError:
                continue
            if sz > 50_000_000:
                continue
            # sniff keys
            keys = []
            try:
                with p.open(encoding="utf-8", errors="replace") as f:
                    for _ in range(5):
                        line = f.readline()
                        if not line.strip():
                            continue
                        try:
                            obj = json.loads(line)
                            if isinstance(obj, dict):
                                keys = sorted(obj.keys())[:12]
                                break
                        except json.JSONDecodeError:
                            continue
            except OSError:
                pass
            jsonl_files.append(
                {
                    "rel": rel,
                    "name": name,
                    "role": "dataset",
                    "bytes": sz,
                    "keys": keys,
                    "depth": rel.count("/"),
                    "usable": bool(
                        set(keys) & {"text", "messages", "instruction", "response", "task"}
                    ),
                }
            )

        elif suf == ".json" and ("manifest" in name.lower() or "finetune" in name.lower()):
            manifests.append(
                {
                    "rel": rel,
                    "name": name,
                    "role": "manifest",
                    "bytes": p.stat().st_size,
                }
            )

    # Prefer product paths
    def rank(e: Dict[str, Any]) -> tuple:
        rel = e.get("rel", "")
        top = rel.split("/", 1)[0]
        pref = 0 if top in {
            "scripts", "training", "realai", "core", "modules", "abilities",
            "agent_tools", "adapters", "aura", "memory",
        } else 1
        return (pref, -int(e.get("usable", True) or 0), -e.get("bytes", 0), rel)

    scripts.sort(key=rank)
    jsonl_files.sort(key=rank)
    usable_jsonl = [j for j in jsonl_files if j.get("usable")]
    extractors = [s for s in scripts if s["role"] == "extract" and s.get("runnable")]
    trainers = [s for s in scripts if s["role"] in {"trainer", "pipeline"} and s.get("runnable")]
    memory = sorted(memory_modules, key=rank)

    # What models need — prioritized ingest list
    model_needs = {
        "jsonl_corpora": [j["rel"] for j in usable_jsonl[:40]],
        "extract_scripts": [s["rel"] for s in extractors[:20]],
        "trainers": [s["rel"] for s in trainers[:20]],
        "memory_modules": [m["rel"] for m in memory[:30]],
        "manifests": [m["rel"] for m in manifests[:20]],
        "recommended_pipeline": [
            "scripts/walk_training_sources.py",
            "scripts/wire_training.py",
            "realai/training/extract_from_agent_tools.py (via wire/ingest)",
            "scripts/train_lora_local.py --preset qwen-coder-1.5b --device directml",
            "C:\\llama-vulkan chat remains on GGUF (Vulkan)",
        ],
    }

    payload = {
        "version": 1,
        "at": utc(),
        "root": str(ROOT),
        "deepen": deepen,
        "counts": {
            "scripts": len(scripts),
            "jsonl": len(jsonl_files),
            "usable_jsonl": len(usable_jsonl),
            "extractors": len(extractors),
            "trainers": len(trainers),
            "memory_modules": len(memory),
            "manifests": len(manifests),
        },
        "model_needs": model_needs,
        "scripts": scripts[:500],
        "jsonl_files": jsonl_files[:300],
        "usable_jsonl": usable_jsonl[:80],
        "extractors": extractors[:40],
        "trainers": trainers[:40],
        "memory_modules": memory[:80],
        "manifests": manifests[:40],
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Training sources walk",
        "",
        f"- at: {payload['at']}",
        f"- scripts: {payload['counts']['scripts']}",
        f"- usable jsonl: {payload['counts']['usable_jsonl']}",
        f"- extractors: {payload['counts']['extractors']}",
        f"- trainers: {payload['counts']['trainers']}",
        f"- memory modules: {payload['counts']['memory_modules']}",
        "",
        "## What models need (priority ingest)",
        "",
        "### JSONL corpora",
    ]
    for r in model_needs["jsonl_corpora"][:25]:
        lines.append(f"- `{r}`")
    lines += ["", "### Extract / learn scripts", ""]
    for r in model_needs["extract_scripts"][:15]:
        lines.append(f"- `{r}`")
    lines += ["", "### Trainers / pipelines", ""]
    for r in model_needs["trainers"][:15]:
        lines.append(f"- `{r}`")
    lines += ["", "### Memory modules (export candidates)", ""]
    for r in model_needs["memory_modules"][:20]:
        lines.append(f"- `{r}`")
    lines += [
        "",
        "## Craft",
        "",
        "- `/dispatch training` — run training ingest + wire + optional train",
        "- `/train-walk` — this walk",
        "- `/train wire` — rebuild LoRA-ready JSONL from discovered sources",
        "",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[train-walk] scripts={payload['counts']['scripts']} usable_jsonl={payload['counts']['usable_jsonl']}")
    print(f"[train-walk] wrote {OUT_JSON}")
    print(f"[train-walk] wrote {OUT_MD}")
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deepen", action="store_true", help="Also scan recovered-like trees")
    args = ap.parse_args()
    walk(deepen=bool(args.deepen))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
