#!/usr/bin/env python3
"""
DDS-3 Deep Gold Map

Why this exists
---------------
Earlier keyword/cavity scripts found "so much more" because they scanned .md/.txt
and nested archives/OG trees. The polished operational DDS-3 skipped those for
speed — correct for boot, incomplete for treasure mapping.

This scan:
  - WALKS nested archive / realai_og_mess / backups / weird trees at any level
  - INCLUDES .md .txt .json .yaml .yml .toml .py .ts .js (and source)
  - SKIPS pure noise: node_modules, venv, site-packages, .next, dist, phase4 previews
  - Does NOT re-hash every hit repeatedly
  - Does NOT delete or move anything

Outputs
-------
  scan_results/dds3_deep_gold_map.json
  scan_results/dds3_deep_gold_map_summary.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Set, Tuple

ROOT = os.environ.get("REALAI_ROOT", r"C:\realai")
OUT_DIR = os.path.join(ROOT, "scan_results")
OUT_FULL = os.path.join(OUT_DIR, "dds3_deep_gold_map.json")
OUT_SUMMARY = os.path.join(OUT_DIR, "dds3_deep_gold_map_summary.json")
OUT_PARTIAL = os.path.join(OUT_DIR, "dds3_deep_gold_map.partial.json")

SKIP_DIR_NAMES = {
    "node_modules", "node_modules.disabled", "venv", ".venv", "env",
    "__pycache__", ".git", ".hg", ".svn", ".tox",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".cache",
    "site-packages", "dist", "build", ".eggs", ".next", ".vs",
    "phase4_tools", "plan_phase4_preview", "scan_results", "terminals",
    "chocolatey", ".blackbox", "rebase_dryrun", "realai_search_temp",
    "Output", ".kilo", "worktrees",
}
SKIP_FRAGMENTS = (".egg-info", "node_modules", "site-packages", "__pycache__", ".next", "pyinstaller")

# Include docs intentionally (this is the cavity-script gold layer)
SCAN_EXT = {
    ".py", ".ts", ".tsx", ".js", ".mjs", ".cjs",
    ".md", ".txt", ".rst",
    ".json", ".yaml", ".yml", ".toml",
    ".cfg", ".ini",
}
# Skip lockfiles / pure dump noise even if .json/.txt
SKIP_FILE_NAMES = {
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "repo_tree.txt", "repo_tree_clean.txt", "repo_tree_filtered.txt",
    "repo_tree_shallow.txt", "allfiles.txt",
}

# Capability / subsystem gold keywords (case-insensitive word-ish)
GOLD_GROUPS: Dict[str, Tuple[str, ...]] = {
    "models_inference": (
        "gguf", "llama", "ollama", "vllm", "llama.cpp", "llama-cli",
        "default_llm", "model_registry", "local model", "embedding",
        "sentence_transformers", "realai-embed", "safetensors",
        "qwen", "mistral", "phi-3", "instruct",
    ),
    "agents_orchestrate": (
        "agent_runtime", "orchestrat", "multi-agent", "planner",
        "executor", "critic", "agentx", "persona",
    ),
    "memory_rag": (
        "memory_engine", "vector", "chromadb", "faiss", "rag_",
        "knowledge_graph", "sqlite_memory", "realai_memory",
    ),
    "tools_mcp_plugins": (
        "mcp_", "plugin", "tool_registry", "agent-tools", "manifest",
    ),
    "server_api_ui": (
        "api_server", "chat/completions", "fusion-ui", "vscode",
        "streaming", "openai-compatible", "/v1/models", "/health",
    ),
    "self_improve_training": (
        "self_improvement", "finetune", "lora", "training", "dataset",
        "evolution", "auto_improv",
    ),
    "world_npc_game": (
        "worldmodel", "world_model", "npc_", "quest_", "atomic fizz",
        "overseer",
    ),
    "web3_solana": (
        "solana", "web3", "anchor", "wallet",
    ),
    "v2_v3_migration": (
        "v2", "v3", "realai 2", "realai 3", "migration", "legacy",
        "port 8082", "port 8000", "took over", "duplicate server",
    ),
    "missing_broken": (
        "todo", "fixme", "missing", "not implemented", "placeholder",
        "deprecated", "broken", "stub",
    ),
}

# Compiled patterns
GROUP_RES = {
    g: [re.compile(re.escape(k), re.I) for k in kws]
    for g, kws in GOLD_GROUPS.items()
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def should_skip_dir(name: str) -> bool:
    low = name.lower()
    if low in SKIP_DIR_NAMES or name in SKIP_DIR_NAMES:
        return True
    if low.endswith(".egg-info"):
        return True
    for frag in SKIP_FRAGMENTS:
        if frag in low:
            return True
    return False


def era_of(rel: str) -> str:
    r = rel.replace("\\", "/").lower()
    if "realai_og_mess" in r:
        return "og_mess"
    if r.startswith("archive/") or "/archive/" in r:
        return "archive"
    if ".backup" in r or "historical_backup" in r:
        return "backup"
    if "__dup" in r or " copy/" in r or r.endswith(" copy"):
        return "duplicate"
    if r.startswith("recovered/"):
        return "recovered"
    if r.startswith("realai/") or r.startswith("core/") or r.startswith("apps/"):
        return "clean"
    if r.startswith("models/"):
        return "models_tree"
    if r.startswith("training/"):
        return "training"
    if r.startswith("docs/") or r.endswith(".md"):
        return "docs"
    return "other"


def walk_files(root: str, dirs_skipped: Counter) -> Iterable[str]:
    for dp, dirnames, filenames in os.walk(root, topdown=True):
        kept = []
        for d in dirnames:
            if should_skip_dir(d):
                dirs_skipped[d] += 1
                continue
            kept.append(d)
        dirnames[:] = kept
        for f in filenames:
            low = f.lower()
            if low in SKIP_FILE_NAMES:
                continue
            _, ext = os.path.splitext(low)
            if ext not in SCAN_EXT:
                continue
            full = os.path.join(dp, f)
            try:
                if os.path.getsize(full) > 3_000_000:  # 3MB text cap
                    continue
            except OSError:
                continue
            yield full


def safe_read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def scan_text(text: str) -> Dict[str, List[dict]]:
    """Return group -> list of {keyword, line, snippet} (capped per group)."""
    hits: Dict[str, List[dict]] = defaultdict(list)
    if not text:
        return hits
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        low = line.lower()
        # cheap prefilter
        if len(line) > 2000:
            line = line[:2000]
        for group, patterns in GROUP_RES.items():
            if len(hits[group]) >= 8:  # cap per file per group
                continue
            for pat, kw in zip(patterns, GOLD_GROUPS[group]):
                if pat.search(line):
                    hits[group].append({
                        "keyword": kw,
                        "line": i,
                        "snippet": line.strip()[:240],
                    })
                    break
    return hits


def run(progress_every: int = 200, checkpoint_every: int = 1000) -> dict:
    t0 = time.time()
    started = utc_now()
    dirs_skipped: Counter = Counter()
    files_scanned = 0
    files_with_gold = 0

    # file records (only files with at least one gold hit)
    file_hits: List[dict] = []
    group_counts: Counter = Counter()
    era_counts: Counter = Counter()
    keyword_counts: Counter = Counter()
    # locations of model-related docs
    model_doc_paths: List[str] = []
    v2v3_hits: List[dict] = []

    print(f"[DEEP-GOLD] root={ROOT}")
    print("[DEEP-GOLD] includes .md/.txt + nested archive/OG; skips node_modules/venv/...")

    for full in walk_files(ROOT, dirs_skipped):
        rel = os.path.relpath(full, ROOT).replace("\\", "/")
        text = safe_read(full)
        hits = scan_text(text)
        files_scanned += 1

        if not hits:
            if progress_every and files_scanned % progress_every == 0:
                print(
                    f"[DEEP-GOLD] scanned={files_scanned} gold_files={files_with_gold} "
                    f"elapsed={time.time()-t0:.1f}s current={rel[:90]}"
                )
            continue

        files_with_gold += 1
        e = era_of(rel)
        era_counts[e] += 1
        groups_present = []
        flat = []
        for g, items in hits.items():
            if not items:
                continue
            groups_present.append(g)
            group_counts[g] += len(items)
            for it in items:
                keyword_counts[it["keyword"]] += 1
                flat.append({"group": g, **it})
                if g == "v2_v3_migration":
                    v2v3_hits.append({"file": rel, "era": e, **it})
            if g == "models_inference":
                model_doc_paths.append(rel)

        file_hits.append({
            "file": rel,
            "era": e,
            "ext": os.path.splitext(rel)[1].lower(),
            "groups": groups_present,
            "hit_count": len(flat),
            "hits": flat[:40],  # cap
        })

        if progress_every and files_scanned % progress_every == 0:
            print(
                f"[DEEP-GOLD] scanned={files_scanned} gold_files={files_with_gold} "
                f"elapsed={time.time()-t0:.1f}s current={rel[:90]}"
            )

        if checkpoint_every and files_scanned % checkpoint_every == 0:
            _write_partial(file_hits, files_scanned, started)

    finished = utc_now()
    elapsed = round(time.time() - t0, 2)

    # rank files by hit_count
    top_files = sorted(file_hits, key=lambda x: -x["hit_count"])[:80]
    # unique model-related paths
    model_docs = sorted(set(model_doc_paths))[:200]

    # gold only outside clean
    only_outside = [f for f in file_hits if f["era"] not in {"clean", "models_tree", "recovered"}]
    only_outside_top = sorted(only_outside, key=lambda x: -x["hit_count"])[:100]

    meta = {
        "mode": "deep_gold",
        "root": ROOT,
        "started": started,
        "finished": finished,
        "elapsed_seconds": elapsed,
        "files_scanned": files_scanned,
        "files_with_gold": files_with_gold,
        "dirs_skipped": dict(dirs_skipped.most_common(40)),
        "preservation_note": (
            "READ-ONLY deep gold map. Scans md/txt + code in archive/OG/nested trees. "
            "Skips node_modules/venv/.next only. Complements operational DDS-3."
        ),
    }

    summary = {
        "meta": meta,
        "group_counts": dict(group_counts.most_common()),
        "era_counts": dict(era_counts.most_common()),
        "top_keywords": [{"keyword": k, "count": n} for k, n in keyword_counts.most_common(60)],
        "top_files": [{"file": f["file"], "era": f["era"], "hit_count": f["hit_count"], "groups": f["groups"]} for f in top_files],
        "model_related_docs": model_docs[:100],
        "only_outside_clean_top": [
            {"file": f["file"], "era": f["era"], "hit_count": f["hit_count"], "groups": f["groups"]}
            for f in only_outside_top[:50]
        ],
        "v2_v3_hit_count": len(v2v3_hits),
        "v2_v3_sample": v2v3_hits[:40],
    }

    full = {
        "meta": meta,
        "summary": summary,
        "files": file_hits[:8000],  # hard cap output size
        "v2_v3_hits": v2v3_hits[:200],
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FULL, "w", encoding="utf-8") as f:
        json.dump(full, f, indent=2)
    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    if os.path.exists(OUT_PARTIAL):
        try:
            os.remove(OUT_PARTIAL)
        except OSError:
            pass

    print(f"[DEEP-GOLD] Complete -> {OUT_FULL}")
    print(f"[DEEP-GOLD] Summary -> {OUT_SUMMARY}")
    print(
        f"[DEEP-GOLD] scanned={files_scanned} gold_files={files_with_gold} "
        f"elapsed={elapsed}s groups={dict(group_counts)}"
    )
    return full


def _write_partial(file_hits, files_scanned, started):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_PARTIAL, "w", encoding="utf-8") as f:
        json.dump({
            "meta": {"partial": True, "files_scanned": files_scanned, "started": started, "checkpoint_at": utc_now()},
            "files": file_hits[-500:],
        }, f)


def main():
    ap = argparse.ArgumentParser(description="DDS-3 deep gold map (md/txt + nested archive/OG, noise skipped)")
    ap.add_argument("--progress-every", type=int, default=300)
    ap.add_argument("--checkpoint-every", type=int, default=1500)
    args = ap.parse_args()
    run(progress_every=args.progress_every, checkpoint_every=args.checkpoint_every)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
