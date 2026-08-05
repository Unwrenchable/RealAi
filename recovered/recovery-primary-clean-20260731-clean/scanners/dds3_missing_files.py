#!/usr/bin/env python3
"""
DDS-3 — Missing-file / reference map (scoped, ability-preserving)

Design goals
------------
1. Finish in minutes, not days: skip pure *noise* only (venv, node_modules, …).
2. Never delete, move, or modify project files — read-only scan.
3. Preserve discovery of multi-era *abilities*:
   - operational mode → clean runtime boot path (fast, actionable)
   - inventory mode  → super-repo minus noise (finds unique/dup knowledge)
   - abilities mode  → index capability tokens across eras (training, memory,
                       agents, tools, models) without resolving every import

All development eras (clean, OG, archives, training, memory schemas) remain
on disk. This scanner only *maps* missing refs so merge can be curated —
bulk smash-merge of 10k files is deliberately NOT the default path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Set, Tuple

ROOT = os.environ.get("REALAI_ROOT", r"C:\realai")
OUT_DIR = os.path.join(ROOT, "scan_results")
OUT_FULL = os.path.join(OUT_DIR, "dds3_missing_files.json")
OUT_SUMMARY = os.path.join(OUT_DIR, "dds3_missing_files_summary.json")
OUT_PARTIAL = os.path.join(OUT_DIR, "dds3_missing_files.partial.json")
OUT_ABILITIES = os.path.join(OUT_DIR, "dds3_ability_inventory.json")
OUT_ARCHIVE = os.path.join(OUT_DIR, "dds3_archive_triage.json")

SKIP_RULES_VERSION = 3

# ---------------------------------------------------------------------------
# Pure NOISE — never scan these. Not "code we might want later".
#
# IMPORTANT: top-level `archive/` is NOT noise. Code was accidentally moved
# there during cleanup; it must be triaged and recoverable. We still prune
# *inside* archive: venv, node_modules, .next, dist, site-packages, etc.
# ---------------------------------------------------------------------------
SKIP_DIR_NAMES: Set[str] = {
    "venv",
    ".venv",
    "env",
    ".env",  # dir name only; files still ok
    "node_modules",
    "node_modules.disabled",
    "__pycache__",
    ".git",
    ".git_disabled",
    ".hg",
    ".svn",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".cache",
    "site-packages",
    "dist",
    "build",
    ".eggs",
    ".next",  # Next.js build output
    ".vs",
    "phase4_tools",  # dry-run diffs, not product code
    "plan_phase4_preview",
    "scan_results",
    "terminals",
    "chocolatey",
    ".blackbox",
    ".backup",
    "rebase_dryrun",
    "realai_search_temp",
    "Output",
    # binary / weight dumps (metadata elsewhere still scanned in inventory)
    "gguf",
    "blobs",
    # IDE / agent worktrees nested inside package (not product eras)
    ".kilo",
    "worktrees",
}

# Directory *name fragments* that almost always mean junk trees
SKIP_DIR_FRAGMENTS: Tuple[str, ...] = (
    ".egg-info",
    "node_modules",
    "site-packages",
    "__pycache__",
    ".pyc",
    "pyinstaller",
    ".next",
)

# Operational roots — clean runtime spine (boot + unify target)
# `archive` is added when --include-archive (default True) for accidental-move recovery.
OPERATIONAL_ROOTS: Tuple[str, ...] = (
    "realai",
    "core",
    "apps",
    "agents",
    "providers",
    "packages",
    "config",
    "schema",
    "plugins",
    "aura",
    "benchmarks",
    "cli",
    "scripts",
    "training",  # intentional: training code is a product ability
    "marketplace",
    "fusion-ui",
    "src",
)

# Root-level files always included in operational mode
OPERATIONAL_ROOT_FILES: Tuple[str, ...] = (
    "api_server.py",
    "main.py",
    "orchestrator.py",
    "local_models.py",
    "realai_local_server.py",
    "realai_server.py",
    "realai_gui.py",
    "router.py",
    "model_registry.py",
    "tools.py",
    "self_improvement.py",
    "manifest.json",
    "models.yaml",
    "providers.yaml",
    "realai.toml",
    "realai.toml.example",
    "pyproject.toml",
    "package.json",
    "requirements.txt",
    "requirements-full.txt",
    "requirements-ci.txt",
    "tools.md",
    "AGENTS.md",
)

SOURCE_EXT: Set[str] = {".py", ".ts", ".tsx", ".js", ".mjs", ".cjs"}
CONFIG_EXT: Set[str] = {".yaml", ".yml", ".toml"}
CONFIG_NAMES: Set[str] = {
    "package.json",
    "manifest.json",
    "pyproject.toml",
    "tsconfig.json",
    "models.json",
    "registry.json",
    "providers.yaml",
    "models.yaml",
}

# Ability tokens — preserve multi-era capability discovery (not full import graph)
ABILITY_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("realai", re.compile(r"\brealai_[a-zA-Z0-9_]+\b")),
    ("worldmodel", re.compile(r"\bworldmodel_[a-zA-Z0-9_]+\b")),
    ("agent", re.compile(r"\bagent_[a-zA-Z0-9_]+\b")),
    ("memory", re.compile(r"\bmemory_[a-zA-Z0-9_]+\b")),
    ("plugin", re.compile(r"\bplugin_[a-zA-Z0-9_]+\b")),
    ("mcp", re.compile(r"\bmcp_[a-zA-Z0-9_]+\b")),
    ("npc", re.compile(r"\bnpc_[a-zA-Z0-9_]+\b")),
    ("quest", re.compile(r"\bquest_[a-zA-Z0-9_]+\b")),
    ("solana", re.compile(r"\bsolana_[a-zA-Z0-9_]+\b")),
    ("lora", re.compile(r"\blora_[a-zA-Z0-9_]+\b")),
    ("rag", re.compile(r"\brag_[a-zA-Z0-9_]+\b")),
    ("training", re.compile(r"\b(train|training|dataset|finetune|fine_tune)_[a-zA-Z0-9_]+\b", re.I)),
    ("class_agent", re.compile(r"\bclass\s+([A-Za-z0-9_]*Agent)\b")),
    ("class_memory", re.compile(r"\bclass\s+([A-Za-z0-9_]*Memory)\b")),
    ("class_tool", re.compile(r"\bclass\s+([A-Za-z0-9_]*Tool)\b")),
    ("class_provider", re.compile(r"\bclass\s+([A-Za-z0-9_]*Provider)\b")),
    ("class_model", re.compile(r"\bclass\s+([A-Za-z0-9_]*Model)\b")),
]

IMPORT_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("import", re.compile(r"^\s*import\s+([a-zA-Z_][a-zA-Z0-9_\.]*)", re.M)),
    ("from_import", re.compile(r"^\s*from\s+([a-zA-Z_][a-zA-Z0-9_\.]*)\s+import", re.M)),
    ("require", re.compile(r"""require\(['"]([^'"]+)['"]\)""")),
    ("es_import", re.compile(r"""import\s+(?:[\s\S]*?\s+from\s+)?['"]([^'"]+)['"]""")),
]

# Relative path refs in config / code strings (limited)
PATH_REF_PATTERN = re.compile(
    r"""['"]((?:\./|\.\./|realai/|core/|apps/|agents/|providers/)[^'"]{1,200})['"]"""
)

# Common noise imports — not "missing RealAI modules"
STDLIB_SKIP: Set[str] = {
    "os", "sys", "re", "json", "ast", "csv", "io", "time", "math", "random",
    "hashlib", "hmac", "base64", "pathlib", "typing", "collections", "functools",
    "itertools", "dataclasses", "enum", "abc", "copy", "uuid", "logging",
    "argparse", "subprocess", "threading", "multiprocessing", "asyncio",
    "http", "urllib", "email", "sqlite3", "pickle", "tempfile", "shutil",
    "glob", "fnmatch", "struct", "socket", "ssl", "queue", "signal", "traceback",
    "warnings", "contextlib", "inspect", "importlib", "pkgutil", "platform",
    "datetime", "decimal", "statistics", "textwrap", "string", "secrets",
    "concurrent", "unittest", "doctest", "pdb", "pprint", "types", "weakref",
    "html", "xml", "zipfile", "tarfile", "gzip", "bz2", "lzma", "configparser",
    "tomllib", "zoneinfo", "dataclasses", "operator", "bisect", "heapq",
    "array", "ctypes", "mmap", "select", "selectors", "errno", "gc",
    "builtins", "__future__", "annotations",
}

THIRD_PARTY_SKIP: Set[str] = {
    "numpy", "np", "pandas", "pd", "torch", "tensorflow", "tf", "sklearn",
    "requests", "httpx", "aiohttp", "flask", "fastapi", "uvicorn", "starlette",
    "pydantic", "yaml", "toml", "dotenv", "click", "rich", "tqdm", "pytest",
    "react", "react-dom", "vue", "angular", "lodash", "express", "next",
    "fs", "path", "util", "crypto", "buffer", "stream", "events", "http",
    "url", "querystring", "child_process", "worker_threads", "net", "tls",
    "vscode", "@types", "esbuild", "tsx", "typescript", "zod", "axios",
    "openai", "anthropic", "groq", "huggingface_hub", "transformers",
    "sentence_transformers", "llama_cpp", "chromadb", "faiss", "redis",
    "psycopg2", "sqlalchemy", "alembic", "celery", "boto3", "botocore",
    "PIL", "cv2", "matplotlib", "seaborn", "scipy", "sympy",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm_rel(path: str, root: str = ROOT) -> str:
    try:
        rel = os.path.relpath(path, root)
    except ValueError:
        rel = path
    return rel.replace("\\", "/")


def should_skip_dir(name: str) -> bool:
    lower = name.lower()
    if lower in SKIP_DIR_NAMES or name in SKIP_DIR_NAMES:
        return True
    if lower.endswith(".egg-info"):
        return True
    for frag in SKIP_DIR_FRAGMENTS:
        if frag in lower:
            return True
    # Nested venv copies named oddly
    if lower in {"lib64", "include"} and False:
        pass
    return False


def is_noise_path(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    for p in parts:
        if should_skip_dir(p):
            return True
        if p.endswith(".egg-info"):
            return True
    return False


def is_scannable_file(name: str, include_config: bool) -> bool:
    lower = name.lower()
    _, ext = os.path.splitext(lower)
    if ext in SOURCE_EXT:
        return True
    if include_config:
        if ext in CONFIG_EXT or lower in CONFIG_NAMES:
            return True
    return False


def top_level_module(ref: str) -> str:
    ref = ref.strip().lstrip("./")
    if not ref:
        return ""
    # strip package subpaths for skip checks
    head = ref.replace("\\", "/").split("/")[0].split(".")[0]
    return head


def should_skip_reference(ref: str) -> bool:
    if not ref or len(ref) > 240:
        return True
    if ref.startswith("node:") or ref.startswith("http:") or ref.startswith("https:"):
        return True
    if ref.startswith("@"):  # scoped npm — third party
        return True
    head = top_level_module(ref)
    if not head or head.startswith("_") and head not in {"__main__", "__init__"}:
        # allow __init__ style but skip private-ish noise
        pass
    if head in STDLIB_SKIP or head in THIRD_PARTY_SKIP:
        return True
    # bare relative single tokens that aren't modules
    if ref in {".", "..", "..."}:
        return True
    return False


def walk_files(
    roots: Iterable[str],
    include_config: bool,
    dirs_skipped: Counter,
) -> Iterable[str]:
    """Yield absolute file paths under roots, pruning noise dirs."""
    for root in roots:
        if not os.path.isdir(root) and not os.path.isfile(root):
            continue
        if os.path.isfile(root):
            if is_scannable_file(os.path.basename(root), include_config):
                yield root
            continue
        for dp, dirnames, filenames in os.walk(root, topdown=True):
            # prune in-place
            kept = []
            for d in dirnames:
                if should_skip_dir(d):
                    dirs_skipped[d] += 1
                    continue
                # skip enormous binary model weight dirs by extension pattern inside name
                if d.lower().endswith((".gguf",)):
                    dirs_skipped[d] += 1
                    continue
                kept.append(d)
            dirnames[:] = kept
            for f in filenames:
                if not is_scannable_file(f, include_config):
                    continue
                full = os.path.join(dp, f)
                rel = norm_rel(full)
                if is_noise_path(rel):
                    continue
                # skip huge files (> 2MB) — not useful source for ref scan
                try:
                    if os.path.getsize(full) > 2_000_000:
                        continue
                except OSError:
                    continue
                yield full


def build_path_index(index_roots: Iterable[str], dirs_skipped: Counter) -> Tuple[Set[str], Set[str]]:
    """
    Index relative paths (posix lower) and module-ish basenames for O(1) exists checks.
    Indexes *code + config* under given roots, still skipping noise dirs.
    Does NOT load file contents.
    """
    rel_paths: Set[str] = set()
    basenames: Set[str] = set()
    for root in index_roots:
        if not os.path.exists(root):
            continue
        if os.path.isfile(root):
            rel = norm_rel(root).lower()
            rel_paths.add(rel)
            basenames.add(os.path.basename(root).lower())
            continue
        for dp, dirnames, filenames in os.walk(root, topdown=True):
            kept = []
            for d in dirnames:
                if should_skip_dir(d):
                    dirs_skipped[d] += 1
                    continue
                kept.append(d)
            dirnames[:] = kept
            for f in filenames:
                full = os.path.join(dp, f)
                rel = norm_rel(full).lower()
                if is_noise_path(rel):
                    continue
                rel_paths.add(rel)
                basenames.add(f.lower())
                # also without extension for module match
                stem, _ = os.path.splitext(f)
                basenames.add(stem.lower())
                # dotted module path variants
                no_ext, _ = os.path.splitext(rel)
                rel_paths.add(no_ext)
                rel_paths.add(no_ext.replace("/", "."))
    return rel_paths, basenames


def ref_exists(ref: str, rel_paths: Set[str], basenames: Set[str], cache: Dict[str, bool]) -> bool:
    if ref in cache:
        return cache[ref]
    if should_skip_reference(ref):
        cache[ref] = True  # treat as "not missing RealAI"
        return True

    candidates = []
    cleaned = ref.strip().replace("\\", "/")
    candidates.append(cleaned.lower())
    candidates.append(cleaned.lstrip("./").lower())

    # python module → path
    if "/" not in cleaned and not cleaned.endswith(tuple(SOURCE_EXT)):
        dotted = cleaned.replace(".", "/")
        for ext in SOURCE_EXT | {""}:
            candidates.append((dotted + ext).lower())
        candidates.append(dotted.lower())
        # package __init__
        candidates.append((dotted + "/__init__.py").lower())

    # with extensions
    for ext in SOURCE_EXT | CONFIG_EXT:
        candidates.append((cleaned + ext).lower())
        candidates.append((cleaned.lstrip("./") + ext).lower())

    found = False
    for c in candidates:
        c = c.lstrip("/")
        if c in rel_paths:
            found = True
            break
        # basename fallback for simple tokens
        base = os.path.basename(c)
        stem, _ = os.path.splitext(base)
        if stem in basenames or base in basenames:
            # only for short project-ish names
            if stem.startswith(("realai", "agent", "memory", "world", "plugin", "mcp", "npc", "quest", "solana", "lora", "rag")):
                found = True
                break

    cache[ref] = found
    return found


def safe_read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def file_hash_once(path: str, cache: Dict[str, Optional[str]]) -> Optional[str]:
    if path in cache:
        return cache[path]
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        cache[path] = h.hexdigest()
    except OSError:
        cache[path] = None
    return cache[path]


def extract_refs(text: str, include_tokens: bool) -> List[Tuple[str, str]]:
    """Return list of (kind, reference)."""
    out: List[Tuple[str, str]] = []
    seen: Set[Tuple[str, str]] = set()

    for kind, pat in IMPORT_PATTERNS:
        for m in pat.findall(text):
            key = (kind, m)
            if key not in seen:
                seen.add(key)
                out.append(key)

    for m in PATH_REF_PATTERN.findall(text):
        key = ("path_ref", m)
        if key not in seen:
            seen.add(key)
            out.append(key)

    if include_tokens:
        for kind, pat in ABILITY_PATTERNS:
            # only realai_* style for missing-file resolution (classes are abilities inventory)
            if kind.startswith("class_"):
                continue
            for m in pat.findall(text):
                token = m if isinstance(m, str) else m
                key = ("token", token)
                if key not in seen:
                    seen.add(key)
                    out.append(key)

    return out


_LEARNED_PATTERNS_CACHE: Optional[List[Tuple[str, re.Pattern]]] = None


def load_learned_ability_patterns() -> List[Tuple[str, re.Pattern]]:
    """Load scan_results/ability_keywords_learned.json for deeper ability scans (Phase 5F)."""
    global _LEARNED_PATTERNS_CACHE
    if _LEARNED_PATTERNS_CACHE is not None:
        return _LEARNED_PATTERNS_CACHE
    path = os.path.join(OUT_DIR, "ability_keywords_learned.json")
    out: List[Tuple[str, re.Pattern]] = []
    if not os.path.isfile(path):
        _LEARNED_PATTERNS_CACHE = out
        return out
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for row in data.get("patterns") or []:
            kind = str(row.get("kind") or "learned")
            rx = row.get("regex")
            if not rx:
                continue
            try:
                # cap runaway patterns; case-insensitive for phrases
                flags = re.I if kind == "phrase" else 0
                out.append((f"learned_{kind}", re.compile(rx, flags)))
            except re.error:
                continue
            if len(out) >= 400:
                break
    except Exception:
        out = []
    _LEARNED_PATTERNS_CACHE = out
    return out


def extract_abilities(text: str, rel_file: str) -> List[dict]:
    hits = []
    for kind, pat in ABILITY_PATTERNS:
        for m in pat.findall(text):
            token = m if isinstance(m, str) else m
            hits.append({
                "kind": kind,
                "token": token,
                "file": rel_file,
            })
    # Phase 5F: learned keywords from technical rundown + external gold
    for kind, pat in load_learned_ability_patterns():
        for m in pat.findall(text):
            token = m if isinstance(m, str) else (m[0] if isinstance(m, tuple) else str(m))
            if not token or len(str(token)) < 3:
                continue
            hits.append({
                "kind": kind,
                "token": str(token)[:120],
                "file": rel_file,
            })
    return hits


def load_external_ability_roots() -> List[str]:
    """Absolute external roots from era_map for abilities scan (outside C:\\realai)."""
    era_path = os.path.join(OUT_DIR, "era_map.json")
    roots: List[str] = []
    if not os.path.isfile(era_path):
        # hard defaults
        for p in (r"C:\tools\realai", r"C:\Users\tsmit\realai", r"C:\Users\tsmit\realai-clean"):
            if os.path.isdir(p):
                roots.append(p)
        return roots
    try:
        with open(era_path, "r", encoding="utf-8") as f:
            era = json.load(f)
        for p in era.get("external_scan_roots_for_abilities") or []:
            if isinstance(p, str) and (os.path.isdir(p) or os.path.isfile(p)):
                roots.append(p)
    except Exception:
        pass
    # de-dupe
    seen = set()
    out = []
    for r in roots:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def era_of(rel: str) -> str:
    rel = rel.replace("\\", "/").lower()
    if rel.startswith("realai_og_mess/") or "/realai_og_mess/" in rel:
        return "og_mess"
    if rel.startswith("archive/") or "/archive/" in rel:
        return "archive"
    if "historical_backup" in rel or rel.startswith(".backup"):
        return "backup"
    if "__dup" in rel or " copy" in rel or rel.endswith(" copy"):
        return "duplicate_tree"
    if rel.startswith("training/") or "/training/" in rel:
        return "training"
    if "memory" in rel.split("/")[0:2]:
        return "memory"
    if rel.startswith("realai/") or rel.startswith("core/") or rel.startswith("apps/"):
        return "clean_runtime"
    return "other"


def operational_scan_roots(
    root: str,
    include_og: bool,
    include_archive: bool = True,
) -> List[str]:
    roots: List[str] = []
    for name in OPERATIONAL_ROOTS:
        p = os.path.join(root, name)
        if os.path.exists(p):
            roots.append(p)
    for name in OPERATIONAL_ROOT_FILES:
        p = os.path.join(root, name)
        if os.path.isfile(p):
            roots.append(p)
    # Nested package mirror: realai/realai is often the deep package
    nested = os.path.join(root, "realai")
    if os.path.isdir(nested):
        roots.append(nested)
    # Accidental-move recovery: top-level archive is first-class, not noise
    if include_archive:
        arch = os.path.join(root, "archive")
        if os.path.isdir(arch):
            roots.append(arch)
    if include_og:
        og = os.path.join(root, "realai_og_mess")
        if os.path.isdir(og):
            roots.append(og)
    # de-dupe preserve order
    seen = set()
    out = []
    for r in roots:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def inventory_scan_roots(root: str, include_og: bool) -> List[str]:
    """Whole super-repo minus noise; OG included unless disabled."""
    roots = [root]
    if not include_og:
        # still scan root but walk will see og — filter in walk via extra skip
        pass
    return roots


def run_missing_scan(
    mode: str,
    include_og: bool,
    include_config: bool,
    include_tokens: bool,
    checkpoint_every: int,
    progress_every: int,
    include_archive: bool = True,
) -> dict:
    started = utc_now()
    t0 = time.time()
    dirs_skipped: Counter = Counter()
    hash_cache: Dict[str, Optional[str]] = {}
    exists_cache: Dict[str, bool] = {}
    missing_rows: List[dict] = []
    files_scanned = 0
    refs_checked = 0

    if mode == "operational":
        scan_roots = operational_scan_roots(
            ROOT, include_og=include_og, include_archive=include_archive
        )
        # Index clean + archive + og so recovery targets resolve if they still exist
        index_roots = operational_scan_roots(ROOT, include_og=True, include_archive=True)
        # Also index top-level packages that might host modules
        for extra in ("realai", "core", "apps", "agents", "providers", "packages", "plugins", "training", "archive"):
            p = os.path.join(ROOT, extra)
            if os.path.exists(p):
                index_roots.append(p)
    else:
        # inventory
        scan_roots = inventory_scan_roots(ROOT, include_og=include_og)
        index_roots = [ROOT]

    print(
        f"[DDS-3] mode={mode} include_og={include_og} "
        f"include_archive={include_archive} root={ROOT}"
    )
    print(f"[DDS-3] Building path index (noise dirs pruned; archive is NOT noise)...")
    rel_paths, basenames = build_path_index(index_roots, dirs_skipped)
    print(f"[DDS-3] Index: {len(rel_paths)} path keys, {len(basenames)} basenames")

    # For inventory without OG, skip og dir during walk
    extra_skip_when_no_og = {"realai_og_mess"} if not include_og else set()

    file_iter = walk_files(scan_roots, include_config=include_config, dirs_skipped=dirs_skipped)

    for full in file_iter:
        rel = norm_rel(full)
        if not include_og and rel.replace("\\", "/").split("/")[0] in extra_skip_when_no_og:
            continue
        # inventory still respects skip set via walk_files

        text = safe_read(full)
        if not text:
            files_scanned += 1
            continue

        fhash = file_hash_once(full, hash_cache)
        refs = extract_refs(text, include_tokens=include_tokens)
        for kind, ref in refs:
            refs_checked += 1
            if should_skip_reference(ref):
                continue
            if ref_exists(ref, rel_paths, basenames, exists_cache):
                continue
            missing_rows.append({
                "reference": ref,
                "kind": kind,
                "from_file": rel,
                "era": era_of(rel),
                "file_hash": fhash,
                "resolved_candidates": [],
            })

        files_scanned += 1
        if progress_every and files_scanned % progress_every == 0:
            elapsed = time.time() - t0
            print(
                f"[DDS-3] scanned={files_scanned} missing={len(missing_rows)} "
                f"refs_checked={refs_checked} elapsed={elapsed:.1f}s "
                f"current={rel[:80]}"
            )

        if checkpoint_every and files_scanned % checkpoint_every == 0:
            _write_partial(missing_rows, files_scanned, mode, started)

    finished = utc_now()
    elapsed = time.time() - t0

    # summary aggregation
    by_ref: Counter = Counter(r["reference"] for r in missing_rows)
    by_kind: Counter = Counter(r["kind"] for r in missing_rows)
    by_era: Counter = Counter(r["era"] for r in missing_rows)
    by_prefix: Counter = Counter()
    for ref, n in by_ref.items():
        pref = ref.split(".")[0].split("/")[0]
        by_prefix[pref] += n

    top_missing = [
        {"reference": ref, "count": n}
        for ref, n in by_ref.most_common(100)
    ]

    meta = {
        "mode": mode,
        "root": ROOT,
        "started": started,
        "finished": finished,
        "elapsed_seconds": round(elapsed, 2),
        "files_scanned": files_scanned,
        "refs_checked": refs_checked,
        "missing_rows": len(missing_rows),
        "unique_missing": len(by_ref),
        "include_og": include_og,
        "include_archive": include_archive,
        "include_config": include_config,
        "include_tokens": include_tokens,
        "skip_rules_version": SKIP_RULES_VERSION,
        "dirs_skipped": dict(dirs_skipped.most_common(50)),
        "preservation_note": (
            "READ-ONLY scan. No files deleted. Noise-only skips (venv/node_modules/.next/etc). "
            "Top-level archive/ is scanned for accidental-move recovery. "
            "OG/training/memory remain on disk. Use --also-archive for full triage."
        ),
    }

    summary = {
        "meta": meta,
        "unique_missing": len(by_ref),
        "by_kind": dict(by_kind),
        "by_era": dict(by_era),
        "by_prefix": dict(by_prefix.most_common(50)),
        "top_missing": top_missing,
    }

    result = {
        "meta": meta,
        "missing": missing_rows,
        "summary": {
            "unique_missing": len(by_ref),
            "by_kind": dict(by_kind),
            "by_era": dict(by_era),
            "by_prefix": dict(by_prefix.most_common(50)),
            "top_missing": top_missing,
        },
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FULL, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    if os.path.exists(OUT_PARTIAL):
        try:
            os.remove(OUT_PARTIAL)
        except OSError:
            pass

    print(f"[DDS-3] Missing File Scan Complete -> {OUT_FULL}")
    print(f"[DDS-3] Summary -> {OUT_SUMMARY}")
    print(
        f"[DDS-3] files={files_scanned} unique_missing={len(by_ref)} "
        f"rows={len(missing_rows)} elapsed={elapsed:.1f}s"
    )
    return result


# Extensions / names treated as recover candidates inside archive
ARCHIVE_SOURCE_EXT: Set[str] = SOURCE_EXT | {".md", ".json", ".yaml", ".yml", ".toml", ".sql", ".sqlite3", ".db"}
ARCHIVE_NOISE_NAMES: Set[str] = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "next-env.d.ts",
}
ARCHIVE_MEMORY_NAMES: Set[str] = {
    "realai_memory.json",
    "realai_memory.db",
    "realai_memory.sqlite3",
    "realai_knowledge_store.json",
}


def classify_archive_file(rel: str, name: str) -> str:
    """Classify a single archive file for triage."""
    lower = name.lower()
    rel_l = rel.replace("\\", "/").lower()
    if lower in ARCHIVE_MEMORY_NAMES or "memory" in lower and lower.endswith((".json", ".db", ".sqlite3", ".sqlite")):
        return "memory_snapshot"
    if lower in ARCHIVE_NOISE_NAMES:
        return "noise_lockfile"
    if any(p in rel_l for p in ("/dist/", "/.next/", "/out/_next/", "/build/", "/site-packages/")):
        return "noise_build"
    if lower.endswith((".toc", ".pkg", ".exe", ".dll", ".so", ".gguf", ".bin")):
        return "noise_binary"
    if lower.endswith(tuple(SOURCE_EXT)):
        return "source_code"
    if lower.endswith((".md", ".rst", ".txt")) and not lower.endswith("license.txt"):
        return "docs"
    if lower.endswith((".yaml", ".yml", ".toml")) or lower in CONFIG_NAMES:
        return "config"
    if lower.endswith(".json"):
        return "json_data"
    return "other"


def run_archive_triage(progress_every: int = 100) -> dict:
    """
    Walk top-level archive/ (noise pruned) and classify files for recovery.

    Goal: surface code / memory / configs accidentally moved into archive
    without treating the whole archive as disposable junk.
    """
    started = utc_now()
    t0 = time.time()
    arch_root = os.path.join(ROOT, "archive")
    if not os.path.isdir(arch_root):
        result = {
            "meta": {
                "mode": "archive_triage",
                "root": ROOT,
                "archive_root": arch_root,
                "started": started,
                "finished": utc_now(),
                "error": "archive/ directory not found",
            },
            "counts": {},
            "recover_candidates": [],
            "only_in_archive": [],
        }
        os.makedirs(OUT_DIR, exist_ok=True)
        with open(OUT_ARCHIVE, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"[DDS-3-ARCHIVE] No archive/ at {arch_root}")
        return result

    dirs_skipped: Counter = Counter()
    hash_cache: Dict[str, Optional[str]] = {}

    # Index clean runtime basenames + relative stems for "already in clean?" check
    clean_roots = []
    for name in ("realai", "core", "apps", "agents", "providers", "packages", "plugins", "training", "cli", "src"):
        p = os.path.join(ROOT, name)
        if os.path.exists(p):
            clean_roots.append(p)
    clean_paths, clean_basenames = build_path_index(clean_roots, dirs_skipped)
    clean_hash_to_paths: Dict[str, List[str]] = defaultdict(list)

    # optional: hash a subset of clean sources for exact-dup detection (basename match first)
    print("[DDS-3-ARCHIVE] Indexing clean runtime for comparison...")
    clean_source_by_base: Dict[str, List[str]] = defaultdict(list)
    for full in walk_files(clean_roots, include_config=True, dirs_skipped=dirs_skipped):
        rel = norm_rel(full)
        base = os.path.basename(full).lower()
        clean_source_by_base[base].append(rel)

    print("[DDS-3-ARCHIVE] Walking archive/ (venv/node_modules/.next pruned, source kept)...")
    by_class: Counter = Counter()
    by_subtree: Counter = Counter()
    recover_candidates: List[dict] = []
    only_in_archive: List[dict] = []
    memory_snaps: List[dict] = []
    duplicate_of_clean: List[dict] = []
    files_seen = 0

    # Broader walk for archive: also pick md/json/memory, not only source/config
    for dp, dirnames, filenames in os.walk(arch_root, topdown=True):
        kept = []
        for d in dirnames:
            if should_skip_dir(d):
                dirs_skipped[d] += 1
                continue
            kept.append(d)
        dirnames[:] = kept

        for f in filenames:
            full = os.path.join(dp, f)
            rel = norm_rel(full)
            if is_noise_path(rel):
                continue
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            # skip huge blobs (>5MB) except known memory json under 20MB
            if size > 5_000_000 and f.lower() not in ARCHIVE_MEMORY_NAMES:
                by_class["skipped_large"] += 1
                continue

            cls = classify_archive_file(rel, f)
            by_class[cls] += 1
            parts = rel.replace("\\", "/").split("/")
            subtree = parts[1] if len(parts) > 1 else "(root)"
            by_subtree[subtree] += 1
            files_seen += 1

            entry = {
                "file": rel,
                "class": cls,
                "subtree": subtree,
                "size": size,
                "basename": f,
            }

            if cls == "memory_snapshot":
                entry["file_hash"] = file_hash_once(full, hash_cache)
                memory_snaps.append(entry)
                recover_candidates.append({**entry, "reason": "memory_or_training_snapshot"})
            elif cls in ("source_code", "docs", "config"):
                base = f.lower()
                in_clean = base in clean_source_by_base
                entry["also_in_clean_as"] = clean_source_by_base.get(base, [])[:5]
                entry["file_hash"] = file_hash_once(full, hash_cache)
                if not in_clean:
                    entry["reason"] = "basename_not_in_clean_runtime"
                    only_in_archive.append(entry)
                    recover_candidates.append(entry)
                else:
                    # check if content might differ (hash vs clean first match)
                    clean_rel = clean_source_by_base[base][0]
                    clean_full = os.path.join(ROOT, clean_rel.replace("/", os.sep))
                    ch = file_hash_once(clean_full, hash_cache)
                    if ch and entry["file_hash"] and ch != entry["file_hash"]:
                        entry["reason"] = "same_name_different_hash_review"
                        entry["clean_hash"] = ch
                        recover_candidates.append(entry)
                    else:
                        entry["reason"] = "duplicate_of_clean"
                        duplicate_of_clean.append(entry)
            elif cls == "json_data" and (
                "agent" in f.lower() or "manifest" in f.lower() or ".agentx" in rel.replace("\\", "/")
            ):
                entry["reason"] = "agent_or_manifest_json"
                recover_candidates.append(entry)

            if progress_every and files_seen % progress_every == 0:
                print(
                    f"[DDS-3-ARCHIVE] files={files_seen} recover={len(recover_candidates)} "
                    f"only_archive={len(only_in_archive)} current={rel[:80]}"
                )

    # agentx / agents.json special case
    for full in walk_files([arch_root], include_config=True, dirs_skipped=dirs_skipped):
        pass  # already covered above with broader walk

    # Sort priority: only_in_archive first, then different hash, then memory
    only_in_archive.sort(key=lambda x: (x.get("class", ""), x["file"]))
    recover_candidates.sort(
        key=lambda x: (
            0 if x.get("reason") == "basename_not_in_clean_runtime" else
            1 if x.get("reason") == "same_name_different_hash_review" else
            2 if x.get("reason") == "memory_or_training_snapshot" else 3,
            x["file"],
        )
    )

    result = {
        "meta": {
            "mode": "archive_triage",
            "root": ROOT,
            "archive_root": arch_root,
            "started": started,
            "finished": utc_now(),
            "elapsed_seconds": round(time.time() - t0, 2),
            "files_classified": files_seen,
            "skip_rules_version": SKIP_RULES_VERSION,
            "dirs_skipped": dict(dirs_skipped.most_common(40)),
            "preservation_note": (
                "READ-ONLY archive triage. archive/ is NOT treated as disposable. "
                "Source/docs/config/memory that are unique or differ from clean runtime "
                "are listed as recover_candidates. Noise (venv/node_modules/.next/dist) pruned. "
                "Nothing is deleted or moved by this scan."
            ),
        },
        "counts": {
            "files_classified": files_seen,
            "by_class": dict(by_class),
            "by_subtree": dict(by_subtree.most_common(40)),
            "recover_candidates": len(recover_candidates),
            "only_in_archive": len(only_in_archive),
            "duplicate_of_clean": len(duplicate_of_clean),
            "memory_snapshots": len(memory_snaps),
        },
        "recover_candidates": recover_candidates[:3000],
        "only_in_archive": only_in_archive[:2000],
        "memory_snapshots": memory_snaps[:500],
        "duplicate_of_clean_sample": duplicate_of_clean[:200],
        "subtrees": [
            {"name": k, "files": n} for k, n in by_subtree.most_common(40)
        ],
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_ARCHIVE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"[DDS-3-ARCHIVE] Complete -> {OUT_ARCHIVE}")
    print(
        f"[DDS-3-ARCHIVE] classified={files_seen} recover={len(recover_candidates)} "
        f"only_in_archive={len(only_in_archive)} memory={len(memory_snaps)} "
        f"elapsed={time.time()-t0:.1f}s"
    )
    return result


def run_abilities_scan(include_og: bool, progress_every: int = 200) -> dict:
    """
    Capability inventory across eras — does NOT resolve missing files.
    Purpose: make sure training, memory, agent, tool, model *abilities*
    from every development iteration are listed before any merge decisions.

    Phase 5F: also walks external_scan_roots_for_abilities from era_map
    (C:\\tools\\realai, Users trees, historical backups, Atomic Fizz, …)
    and applies learned keyword patterns.
    """
    started = utc_now()
    t0 = time.time()
    dirs_skipped: Counter = Counter()
    # Always index whole repo minus noise so no ability tree is invisible
    roots = [ROOT]
    external = load_external_ability_roots()
    for er in external:
        if er not in roots:
            roots.append(er)
    learned_n = len(load_learned_ability_patterns())
    if not include_og:
        # still walk root; filter og paths if requested
        pass

    token_to_files: Dict[str, Set[str]] = defaultdict(set)
    token_to_eras: Dict[str, Set[str]] = defaultdict(set)
    token_kind: Dict[str, str] = {}
    files_scanned = 0

    print(
        f"[DDS-3-ABILITIES] Scanning capability tokens (noise pruned, nothing deleted)... "
        f"roots={len(roots)} learned_patterns={learned_n} external={len(external)}"
    )
    for er in external:
        print(f"[DDS-3-ABILITIES] external root: {er}")

    def era_for_path(full: str, rel: str) -> str:
        # external absolute paths
        fl = full.replace("/", "\\").lower()
        if "\\tools\\realai" in fl:
            return "tools_cli"
        if "realai_historical_backups" in fl:
            return "historical_backup"
        if "realai-sync-" in fl or "\\backups\\" in fl:
            return "sync_backup"
        if "atomic-fizz" in fl or "unwrenchable" in fl:
            return "atomic_fizz"
        if "\\.realai" in fl or "\\.agentx" in fl:
            return "runtime_state"
        if "\\users\\tsmit\\realai-clean" in fl:
            return "users_realai_clean"
        if "\\users\\tsmit\\realai" in fl:
            return "users_realai"
        return era_of(rel)

    for root in roots:
        file_iter = walk_files([root], include_config=True, dirs_skipped=dirs_skipped)
        for full in file_iter:
            if root == ROOT:
                rel = norm_rel(full)
            else:
                # keep absolute-ish label so external files are visible
                rel = full.replace("\\", "/")
                if rel.startswith("/mnt/c/"):
                    rel = "C:/" + rel[len("/mnt/c/") :]
            if not include_og and "realai_og_mess" in rel.replace("\\", "/"):
                continue
            text = safe_read(full)
            if not text:
                files_scanned += 1
                continue
            era = era_for_path(full, rel if root == ROOT else full)
            for hit in extract_abilities(text, rel):
                tok = hit["token"]
                token_to_files[tok].add(rel)
                token_to_eras[tok].add(era)
                token_kind[tok] = hit["kind"]
            files_scanned += 1
            if progress_every and files_scanned % progress_every == 0:
                print(
                    f"[DDS-3-ABILITIES] files={files_scanned} tokens={len(token_to_files)} "
                    f"current={rel[:80]}"
                )

    # unique vs multi-era
    multi_era = []
    single_era = []
    for tok, eras in token_to_eras.items():
        entry = {
            "token": tok,
            "kind": token_kind.get(tok),
            "eras": sorted(eras),
            "file_count": len(token_to_files[tok]),
            "sample_files": sorted(token_to_files[tok])[:8],
        }
        if len(eras) > 1:
            multi_era.append(entry)
        else:
            single_era.append(entry)

    multi_era.sort(key=lambda x: (-x["file_count"], x["token"]))
    single_era.sort(key=lambda x: (-x["file_count"], x["token"]))

    # tokens that exist ONLY outside clean_runtime — high risk of loss if only clean is kept
    only_outside_clean = [
        e for e in single_era
        if e["eras"] and e["eras"][0] != "clean_runtime"
    ]
    only_outside_clean.sort(key=lambda x: (-x["file_count"], x["token"]))

    result = {
        "meta": {
            "mode": "abilities",
            "root": ROOT,
            "started": started,
            "finished": utc_now(),
            "elapsed_seconds": round(time.time() - t0, 2),
            "files_scanned": files_scanned,
            "unique_tokens": len(token_to_files),
            "include_og": include_og,
            "external_roots": external,
            "learned_patterns": learned_n,
            "skip_rules_version": SKIP_RULES_VERSION,
            "dirs_skipped": dict(dirs_skipped.most_common(50)),
            "preservation_note": (
                "READ-ONLY ability inventory. Lists multi-era capability tokens "
                "(agents/memory/training/tools/…). Tokens only found outside "
                "clean_runtime are high-priority preserve/port candidates. "
                "External machine roots (tools CLI, Users trees, backups, Atomic Fizz) "
                "included when present in era_map. Nothing is deleted or merged by this scan."
            ),
        },
        "multi_era_abilities": multi_era[:5000],
        "only_outside_clean": only_outside_clean[:5000],
        "single_era_sample": single_era[:2000],
        "counts": {
            "multi_era": len(multi_era),
            "single_era": len(single_era),
            "only_outside_clean": len(only_outside_clean),
        },
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_ABILITIES, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"[DDS-3-ABILITIES] Complete -> {OUT_ABILITIES}")
    print(
        f"[DDS-3-ABILITIES] tokens={len(token_to_files)} multi_era={len(multi_era)} "
        f"only_outside_clean={len(only_outside_clean)} elapsed={time.time()-t0:.1f}s"
    )
    return result


def _write_partial(missing_rows: List[dict], files_scanned: int, mode: str, started: str) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    payload = {
        "meta": {
            "partial": True,
            "mode": mode,
            "started": started,
            "checkpoint_at": utc_now(),
            "files_scanned": files_scanned,
            "missing_rows": len(missing_rows),
        },
        "missing": missing_rows,
    }
    with open(OUT_PARTIAL, "w", encoding="utf-8") as f:
        json.dump(payload, f)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "DDS-3 missing-file map + ability inventory + archive triage. "
            "Read-only. Skips pure noise only. Never deletes code, training, memory, or archive."
        )
    )
    p.add_argument(
        "--mode",
        choices=("operational", "inventory", "abilities", "archive"),
        default="operational",
        help=(
            "operational=clean runtime + archive recovery (default); "
            "inventory=super-repo minus noise; "
            "abilities=capability tokens multi-era; "
            "archive=triage archive/ for accidental moves"
        ),
    )
    p.add_argument(
        "--include-og",
        action="store_true",
        help="Include realai_og_mess in scan roots (recommended for abilities/inventory)",
    )
    p.add_argument(
        "--no-archive",
        action="store_true",
        help="Exclude top-level archive/ from operational scan (NOT recommended)",
    )
    p.add_argument(
        "--no-config",
        action="store_true",
        help="Skip yaml/toml/package.json config files",
    )
    p.add_argument(
        "--no-tokens",
        action="store_true",
        help="Skip realai_*/agent_* token patterns in missing-file mode",
    )
    p.add_argument("--checkpoint-every", type=int, default=500)
    p.add_argument("--progress-every", type=int, default=100)
    p.add_argument(
        "--also-abilities",
        action="store_true",
        help="After missing-file scan, also run abilities inventory (recommended)",
    )
    p.add_argument(
        "--also-archive",
        action="store_true",
        help="After missing-file scan, also run archive triage (recommended)",
    )
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    if not os.path.isdir(ROOT):
        print(f"[DDS-3] ROOT not found: {ROOT}", file=sys.stderr)
        return 2

    include_og = args.include_og
    include_archive = not args.no_archive
    if args.mode == "abilities" and not args.include_og:
        include_og = True  # safer default for ability preservation
        print("[DDS-3] abilities mode: defaulting include_og=True")

    if args.mode == "abilities":
        run_abilities_scan(include_og=include_og, progress_every=args.progress_every)
        return 0

    if args.mode == "archive":
        run_archive_triage(progress_every=args.progress_every)
        return 0

    run_missing_scan(
        mode=args.mode,
        include_og=include_og,
        include_config=not args.no_config,
        include_tokens=not args.no_tokens,
        checkpoint_every=args.checkpoint_every,
        progress_every=args.progress_every,
        include_archive=include_archive,
    )

    # Default: also triage archive after operational (accidental-move recovery)
    if args.also_archive or (args.mode == "operational" and include_archive):
        run_archive_triage(progress_every=args.progress_every)

    if args.also_abilities:
        # Full ability map including OG so nothing intended is invisible
        run_abilities_scan(include_og=True, progress_every=args.progress_every)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
