#!/usr/bin/env python3
"""
Local keyword gold scan — find lost RealAI core across Users + key C:\\ roots.

Filename + shallow content hits. Skips venv/node_modules/Windows system noise.
Outputs scan_results/local_keyword_gold_map.json + .md
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "scan_results"
STAGE = ROOT / "recovered" / "from_local_keyword_scan"

# High-value name / path tokens
NAME_KW = [
    "realai",
    "api_server",
    "orchestr",
    "embeddings",
    "embed",
    "agent_tools",
    "agent-tools",
    "self_heal",
    "self_improve",
    "self_extend",
    "self_repair",
    "world_model",
    "aura_memory",
    "local_llama",
    "model_registry",
    "tools_runtime",
    "deepen",
    "provider",
    "bootstrap",
    "openclaw",
    "gguf",
    "lora",
    "finetun",
    "vulkan",
    "llama-server",
    "capability",
    "memory_store",
    "agent_runtime",
    "realai_agent",
    "mcp_server",
    "device_selector",
    "lambda_embeddings",
    "policy.json",
    "sanity_check",
]

# Content keywords (for text-ish files only)
CONTENT_KW = [
    r"realai",
    r"/v1/chat/completions",
    r"/v1/embeddings",
    r"v3_orchestrator",
    r"self_heal",
    r"self_improvement",
    r"agent_tools",
    r"world_model",
    r"llama-server",
    r"REALAI_VULKAN",
    r"deepen_cycle",
    r"model_catalog",
    r"ability_catalog",
    r"create_embeddings",
    r"local.?first",
    r"OpenAI.?compatible",
]

CONTENT_RE = re.compile("|".join(f"({k})" for k in CONTENT_KW), re.I)

SKIP_DIR = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".venv-new",
    ".venv-directml-train",
    "site-packages",
    "dist-info",
    "AppData",  # too huge/noisy unless we special-case
    "Windows",
    "Windows.old",
    "Program Files",
    "Program Files (x86)",
    "ProgramData",
    "$Recycle.Bin",
    "System Volume Information",
    "Recovery",
    "PerfLogs",
    "Cache",
    "cache",
    "CachedData",
    "Code Cache",
    "GPUCache",
    "CrashDumps",
    "Temp",
    "tmp",
    "INetCache",
    "Packages",  # store apps
    ".nuget",
    ".npm",
    ".cargo",
    ".rustup",
    "OneDriveTemp",
}

# Allow limited AppData Local realai-ish paths via explicit roots
TEXT_EXT = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".jsonl", ".yaml", ".yml",
    ".md", ".txt", ".toml", ".ps1", ".bat", ".sh", ".env", ".ini", ".cfg",
    ".html", ".css", ".rs", ".go", ".java", ".cs",
}
GOLD_EXT = TEXT_EXT | {".gguf", ".safetensors", ".bin", ".pt", ".onnx", ".vsix"}

MAX_CONTENT_BYTES = 256_000
MAX_FILES_PER_ROOT = 80_000
MAX_HITS = 25_000


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def roots() -> List[Path]:
    users = Path("/mnt/c/Users/tsmit")
    c = Path("/mnt/c")
    paths = [
        users / "Desktop",
        users / "Documents",
        users / "Downloads",
        users / "realai",
        users / "realai-clean",
        users / ".realai",
        users / ".openclaw",
        users / ".grok",
        users / ".local",
        users / ".config",
        users / ".cache" / "huggingface",
        users / "AppData" / "Local" / "realai",
        users / "AppData" / "Roaming" / "realai",
        users / "AppData" / "Local" / "Programs",
        users / "ATOMIC-FIZZ-CAPS-OLD",
        users / "ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS",
        users / "Scripts",
        users / "EditPro",
        c / "realai",
        c / "tools",
        c / "models",
        c / "llama",
        c / "llama-vulkan",
        c / "llama.cpp",
        c / "temp",
        c / "tmp",
        c / "build",
        c / "DirectML",
        c / "home",
        c / "Users" / "tsmit" / "Meta-Llama-3-70B-Instruct",
    ]
    # Also top-level user dirs that look like gold
    if users.is_dir():
        for child in users.iterdir():
            try:
                if not child.is_dir():
                    continue
                n = child.name.lower()
                if any(k in n for k in ("realai", "agent", "fizz", "openclaw", "llama", "ai-", "grok")):
                    paths.append(child)
            except OSError:
                continue
    # Dedup existing
    seen: Set[str] = set()
    out: List[Path] = []
    for p in paths:
        try:
            rp = str(p.resolve()) if p.exists() else str(p)
        except OSError:
            rp = str(p)
        if rp in seen:
            continue
        seen.add(rp)
        if p.exists():
            out.append(p)
    return out


def name_score(path: Path) -> Tuple[int, List[str]]:
    s = str(path).lower().replace("\\", "/")
    hits = [k for k in NAME_KW if k in s]
    # weight stronger tokens
    score = 0
    for h in hits:
        if h in ("realai", "api_server", "v3_orchestr", "agent_tools", "self_heal", "world_model", "embeddings"):
            score += 5
        elif h in ("gguf", "lora", "orchestr", "provider", "bootstrap", "openclaw"):
            score += 3
        else:
            score += 2
    # file type bonus
    if path.suffix.lower() in {".py", ".ts", ".gguf", ".safetensors", ".json"}:
        score += 2
    if path.suffix.lower() == ".gguf":
        score += 8
    return score, hits


def content_score(path: Path) -> Tuple[int, List[str]]:
    if path.suffix.lower() not in TEXT_EXT:
        return 0, []
    try:
        size = path.stat().st_size
        if size <= 0 or size > MAX_CONTENT_BYTES:
            return 0, []
        raw = path.read_bytes()[:MAX_CONTENT_BYTES]
        # skip binary-ish
        if b"\x00" in raw[:4096]:
            return 0, []
        text = raw.decode("utf-8", errors="ignore")
    except OSError:
        return 0, []
    found = sorted({m.group(0).lower() for m in CONTENT_RE.finditer(text)})
    return min(20, len(found) * 3), found


def walk_root(root: Path, t0: float, deadline: float) -> Iterable[Path]:
    n = 0
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        if time.time() > deadline:
            return
        # prune
        pruned = []
        for d in list(dirnames):
            if d in SKIP_DIR or d.startswith(".") and d not in {".realai", ".openclaw", ".grok", ".config", ".local", ".cache", ".github", ".kilo"}:
                # keep some dotdirs of interest
                if d not in {".realai", ".openclaw", ".grok", ".config", ".local", ".cache", ".github", ".kilo", ".continue"}:
                    continue
            if d.lower().endswith((".dist-info", ".egg-info")):
                continue
            pruned.append(d)
        dirnames[:] = pruned
        for fn in filenames:
            n += 1
            if n > MAX_FILES_PER_ROOT:
                return
            if time.time() > deadline:
                return
            p = Path(dirpath) / fn
            ext = p.suffix.lower()
            # always consider keyword names; skip huge unknown binaries
            try:
                if ext not in GOLD_EXT and not any(k in fn.lower() for k in NAME_KW):
                    continue
                if p.stat().st_size > 20 * 1024**3:  # >20GB skip
                    continue
            except OSError:
                continue
            yield p


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    STAGE.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    # total budget ~12 minutes wall for full multi-root
    per_root_budget = 90.0  # seconds
    all_roots = roots()
    print(f"scanning {len(all_roots)} roots…", flush=True)

    hits: List[Dict[str, Any]] = []
    by_kw: Counter = Counter()
    by_root: Counter = Counter()
    seen_hash: Set[str] = set()
    files_seen = 0

    for root in all_roots:
        deadline = time.time() + per_root_budget
        print(f"  root: {root}", flush=True)
        root_hits = 0
        try:
            for p in walk_root(root, t0, deadline):
                files_seen += 1
                ns, nh = name_score(p)
                if ns < 2:
                    # still allow content scan for .py under realai-ish dirs
                    if "realai" not in str(p).lower() and p.suffix.lower() != ".py":
                        continue
                cs, ch = (0, [])
                if ns >= 3 or "realai" in str(p).lower():
                    cs, ch = content_score(p)
                score = ns + cs
                if score < 4 and not (p.suffix.lower() == ".gguf"):
                    continue
                try:
                    st = p.stat()
                    size = st.st_size
                    mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
                except OSError:
                    size, mtime = 0, None
                # hash small text for dedupe
                h = ""
                if size and size < 2_000_000 and p.suffix.lower() in TEXT_EXT:
                    try:
                        h = hashlib.sha1(p.read_bytes()[:200_000]).hexdigest()[:16]
                        if h in seen_hash:
                            continue
                        seen_hash.add(h)
                    except OSError:
                        pass
                rec = {
                    "path": str(p).replace("/mnt/c/", "C:/").replace("/", "\\") if str(p).startswith("/mnt/c/") else str(p),
                    "posix": str(p),
                    "name": p.name,
                    "ext": p.suffix.lower(),
                    "size": size,
                    "mtime": mtime,
                    "score": score,
                    "name_hits": nh,
                    "content_hits": ch,
                    "root": str(root).replace("/mnt/c/", "C:/").replace("/", "\\") if str(root).startswith("/mnt/c/") else str(root),
                }
                hits.append(rec)
                root_hits += 1
                for k in nh + ch:
                    by_kw[k] += 1
                by_root[rec["root"]] += 1
                if len(hits) >= MAX_HITS:
                    break
        except Exception as e:
            print(f"  ERR {root}: {e}", flush=True)
        print(f"    hits+={root_hits} total_hits={len(hits)} files_seen={files_seen}", flush=True)
        if len(hits) >= MAX_HITS:
            break

    hits.sort(key=lambda r: (-r["score"], -r.get("size") or 0))

    # Priority buckets
    p0_names = {
        "self_extend_tool.py", "self_repair_tool.py", "system_scan_tool.py",
        "aura_memory.py", "lambda_embeddings_audio.py", "local_llama.py",
        "world_model.json", "device_selector.py", "mcp_server.py",
        "find_realai_bootstrap.py", "api_server.py", "v3_orchestrator.py",
        "deepen_cycle.py", "model_catalog.py", "ability_catalog.py",
    }
    p0_hits = [h for h in hits if h["name"].lower() in {n.lower() for n in p0_names}]
    gguf_hits = [h for h in hits if h["ext"] == ".gguf"]
    py_core = [h for h in hits if h["ext"] == ".py" and h["score"] >= 8][:200]

    # Stage unique high-score text files not already under C:\realai
    staged = []
    for h in hits[:400]:
        if h["ext"] not in TEXT_EXT:
            continue
        if h["score"] < 10:
            continue
        src = Path(h["posix"])
        if not src.is_file():
            continue
        # skip already in live realai package (keep discovery only)
        if "/mnt/c/realai/realai/" in h["posix"] and "recovered" not in h["posix"]:
            continue
        if src.stat().st_size > 5_000_000:
            continue
        rel = re.sub(r"[^A-Za-z0-9._-]+", "_", h["path"])[-180:]
        dest = STAGE / rel
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                dest.write_bytes(src.read_bytes())
            staged.append({"src": h["path"], "dest": str(dest), "score": h["score"]})
        except OSError:
            continue

    report = {
        "generated_at": utc(),
        "duration_sec": round(time.time() - t0, 1),
        "roots_scanned": [str(r) for r in all_roots],
        "files_seen": files_seen,
        "hit_count": len(hits),
        "by_keyword": by_kw.most_common(80),
        "by_root": by_root.most_common(40),
        "p0_filename_hits": p0_hits[:100],
        "gguf_hits": gguf_hits[:50],
        "top_hits": hits[:300],
        "py_core_sample": py_core[:100],
        "staged_count": len(staged),
        "staged_sample": staged[:40],
        "stage_dir": str(STAGE),
    }

    OUT.joinpath("local_keyword_gold_map.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    # slim path list
    OUT.joinpath("local_keyword_gold_paths.txt").write_text(
        "\n".join(f"{h['score']}\t{h['path']}" for h in hits[:2000]),
        encoding="utf-8",
    )

    # markdown summary
    lines = [
        "# Local keyword gold scan",
        "",
        f"Generated: {report['generated_at']}",
        f"Duration: {report['duration_sec']}s",
        f"Roots: {len(all_roots)}",
        f"Files seen: {files_seen}",
        f"Hits: {len(hits)}",
        f"Staged text files: {len(staged)} → `{STAGE}`",
        "",
        "## Top keywords",
        "",
    ]
    for k, v in by_kw.most_common(30):
        lines.append(f"- **{k}**: {v}")
    lines += ["", "## P0 filename hits", ""]
    if not p0_hits:
        lines.append("_none_")
    for h in p0_hits[:40]:
        lines.append(f"- score={h['score']} `{h['path']}`")
    lines += ["", "## GGUF hits", ""]
    for h in gguf_hits[:30]:
        gb = round((h["size"] or 0) / 1e9, 2)
        lines.append(f"- {gb}GB `{h['path']}`")
    lines += ["", "## Top overall hits", ""]
    for h in hits[:60]:
        lines.append(
            f"- **{h['score']}** `{h['name']}` — {h['path'][:140]}"
            f"  \n  name:{','.join(h['name_hits'][:6])} content:{','.join(h['content_hits'][:6])}"
        )
    OUT.joinpath("local_keyword_gold_map.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "hits": len(hits),
        "files_seen": files_seen,
        "p0": len(p0_hits),
        "gguf": len(gguf_hits),
        "staged": len(staged),
        "duration": report["duration_sec"],
        "out": str(OUT / "local_keyword_gold_map.json"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
