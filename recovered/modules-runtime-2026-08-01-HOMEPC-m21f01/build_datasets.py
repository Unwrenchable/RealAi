#!/usr/bin/env python3
"""
build_datasets.py - FIXED standalone version (no relative imports)
Deep repo explorer for RealAI training data.
"""

import os
import json
import re
import hashlib
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Set

REPO_ROOT = Path(__file__).parent.resolve()
OUTPUT_DATASET = REPO_ROOT / "dataset.jsonl"
BACKUP_DATASET = REPO_ROOT / f"dataset.jsonl.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "env", "node_modules", "build", "dist", "checkpoints", "checkpoints_lora", "artifacts", ".idea", ".vscode", "logs"}

TEXT_EXTS = {".py", ".md", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".code-search"}

PRIORITY_KEYWORDS = ["deep dice", "progression", "evolution", "realai 3.0", "hive mind", "agentic", "self-improvement", "manifest", "hybrid mode"]

MAX_EXAMPLES = 8000
MAX_CHARS_PER_EXAMPLE = 2800
MIN_CHARS_PER_EXAMPLE = 120

def is_junk_dir(d: str) -> bool:
    return any(skip in d.lower() for skip in SKIP_DIRS)

def get_content_hash(t: str) -> str:
    return hashlib.md5(t.encode('utf-8', errors='ignore')).hexdigest()

def chunk_text(text: str, max_chars: int = MAX_CHARS_PER_EXAMPLE) -> List[str]:
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        cut = text.rfind('\n\n', start, end)
        if cut == -1:
            cut = text.rfind('\n', start, end)
        if cut == -1 or cut < start + max_chars // 2:
            cut = end
        chunk = text[start:cut].strip()
        if len(chunk) >= MIN_CHARS_PER_EXAMPLE:
            chunks.append(chunk)
        start = cut
    return chunks

def extract_from_file(p: Path) -> List[str]:
    try:
        if p.suffix in {".json", ".jsonl"}:
            with p.open(encoding="utf-8", errors="ignore") as f:
                if p.suffix == ".jsonl":
                    return [line.strip() for line in f if line.strip()]
                else:
                    data = json.load(f)
                    return [json.dumps(data, ensure_ascii=False)] if isinstance(data, (dict, list)) else [str(data)]
        else:
            return [p.read_text(encoding="utf-8", errors="ignore")]
    except Exception:
        return []

def generate_manifest_examples(manifest_path: Path) -> List[Dict]:
    examples = []
    try:
        manifests = json.loads(manifest_path.read_text(encoding="utf-8"))
        for m in manifests if isinstance(manifests, list) else [manifests]:
            if not isinstance(m, dict):
                continue
            role = m.get("role", m.get("id", "agent"))
            desc = m.get("description", "")
            tools = m.get("required_tools", [])
            text = f"""You are the {role} agent.\nDescription: {desc}\nTools: {tools}\nReason step-by-step and use tools when needed. Stay in character."""
            examples.append({"text": text})
    except Exception as e:
        print(f"Manifest warning: {e}")
    return examples

def build_dataset():
    print("=== RealAI Dataset Builder (Standalone) ===")
    if OUTPUT_DATASET.exists():
        print("Backing up old dataset...")
        OUTPUT_DATASET.rename(BACKUP_DATASET)

    all_examples = []
    seen = set()

    # Agent manifests first
    for mf in REPO_ROOT.rglob("*manifest*finetuning*.json"):
        print(f"Processing manifest: {mf.name}")
        for ex in generate_manifest_examples(mf):
            h = get_content_hash(ex["text"])
            if h not in seen:
                seen.add(h)
                all_examples.append(ex)

    # Scan everything else
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if not is_junk_dir(d)]
        for fname in files:
            p = Path(root) / fname
            if p.suffix.lower() not in TEXT_EXTS:
                continue
            for content in extract_from_file(p):
                for chunk in chunk_text(content):
                    h = get_content_hash(chunk)
                    if h not in seen and len(chunk) >= MIN_CHARS_PER_EXAMPLE:
                        seen.add(h)
                        all_examples.append({"text": chunk})
                        if len(all_examples) >= MAX_EXAMPLES:
                            break
                if len(all_examples) >= MAX_EXAMPLES:
                    break
            if len(all_examples) >= MAX_EXAMPLES:
                break

    with OUTPUT_DATASET.open("w", encoding="utf-8") as f:
        for ex in all_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"✅ Done! Created dataset.jsonl with {len(all_examples)} examples")
    print(f"Backup: {BACKUP_DATASET.name}")

if __name__ == "__main__":
    build_dataset()