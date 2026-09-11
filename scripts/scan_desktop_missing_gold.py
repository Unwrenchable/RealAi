#!/usr/bin/env python3
"""
Scan Desktop / OneDrive Desktop / user gold roots for missing RealAI core files.

Part of self-heal discover loop:
  python scanners/scan_desktop_missing_gold.py

Outputs:
  scan_results/desktop_missing_gold_map.json
  scan_results/desktop_missing_gold_map.md
  recovered/from_desktop_missing/  (staged copies of high-value uniques)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_ROOT = Path(__file__).resolve().parents[1]
_SCAN = _ROOT / "scan_results"
_STAGE = _ROOT / "recovered" / "from_desktop_missing"
_LIVE = _ROOT / "realai"

# Primary mission roots (user-requested + related)
DEFAULT_ROOTS = [
    Path(r"/mnt/c/Users/tsmit/OneDrive/Desktop"),
    Path(r"/mnt/c/Users/tsmit/Desktop"),
    Path(r"/mnt/c/Users/tsmit/OneDrive/Documents"),
    Path(r"/mnt/c/Users/tsmit/Documents"),
    Path(r"/mnt/c/Users/tsmit/Downloads"),
    Path(r"/mnt/c/Users/tsmit/OneDrive"),
    Path(r"/mnt/c/Users/tsmit/Scripts"),
    Path(r"/mnt/c/Users/tsmit/EditPro"),
    Path(r"/mnt/c/Users/tsmit/ATOMIC-FIZZ-CAPS-OLD"),
    Path(r"/mnt/c/Users/tsmit/ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS"),
    Path(r"/mnt/c/Users/tsmit/.realai"),
    Path(r"/mnt/c/Users/tsmit/.openclaw"),
    Path(r"/mnt/c/Users/tsmit/.grok/worktrees"),
    Path(r"/mnt/c/Users/tsmit/realai"),
    Path(r"/mnt/c/Users/tsmit/realai-clean"),  # clean-era authority tree
    Path(r"/mnt/c/Users/tsmit/realai_historical_backups"),
    Path(r"/mnt/c/Users/tsmit/backups"),
    Path(r"/mnt/c/Users/tsmit/Documents/GitHub/realai"),
    Path(r"/mnt/c/Users/tsmit/projects/realai-clean"),
    Path(r"/mnt/c/tools/realai"),
    Path(r"/mnt/c/temp"),
]

# Missing-priority filenames from kilo forensics + core stack
P0_NAMES = {
    "self_extend_tool.py",
    "self_repair_tool.py",
    "system_scan_tool.py",
    "aura_memory.py",
    "lambda_embeddings_audio.py",
    "local_llama.py",
    "world_model.json",
    "world_model.py",
    "device_selector.py",
    "mcp_server.py",
    "find_realai_bootstrap.py",
    "api_server.py",
    "realai_server.py",
    "v3_orchestrator.py",
    "deepen_cycle.py",
    "model_catalog.py",
    "ability_catalog.py",
    "agent_runtime.py",
    "self_improvement.py",
    "tools_runtime.py",
    "embeddings.py",
    "embeddings_backend.py",
    "memory_store.py",
    "orchestration.py",
    "local_models.py",
    "policy.json",
    "sanity_check.py",
    "agents.json",
    "access_profiles.json",
    "agent_manifests_for_finetuning.json",
}

NAME_TOKENS = [
    "realai", "api_server", "orchestr", "embed", "agent_tools", "agent-tools",
    "self_heal", "self_improve", "world_model", "aura", "local_llama",
    "provider", "bootstrap", "openclaw", "fizz", "gguf", "lora", "finetun",
    "deepen", "capability", "agent_runtime", "mcp_server", "vulkan",
]

SKIP_DIR = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "site-packages",
    "Cache", "cache", "GPUCache", "Code Cache", "INetCache", "Temp", "tmp",
    "$Recycle.Bin", "Windows", "Program Files", "Program Files (x86)",
    "System Volume Information", ".npm", ".nuget", "pictures", "Pictures",
    "Videos", "Music", "GameDVR", "SCREENSHOTS", "WPSystem",
}

TEXT_EXT = {
    ".py", ".ts", ".tsx", ".js", ".json", ".jsonl", ".yaml", ".yml", ".md",
    ".txt", ".toml", ".ps1", ".bat", ".sh", ".html",
}
STAGE_EXT = TEXT_EXT | {".gguf", ".safetensors"}

MAX_STAGE_BYTES = 8_000_000
MAX_WALK_FILES = 120_000


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def win_path(p: Path) -> str:
    s = str(p)
    if s.startswith("/mnt/c/"):
        return "C:\\" + s[len("/mnt/c/") :].replace("/", "\\")
    return s


def load_missing_names() -> Set[str]:
    names = set(P0_NAMES)
    for rel in (
        "kilo_gold_not_found_files.txt",
        "kilo_still_missing_gold.txt",
        "dds3_missing_files_summary.json",
    ):
        p = _SCAN / rel
        if not p.is_file():
            continue
        try:
            if p.suffix == ".json":
                data = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
                # best-effort extract names
                blob = json.dumps(data)
                for m in re.findall(r"([A-Za-z0-9_\-]+\.(?:py|json|ts|md|yaml))", blob):
                    names.add(m)
            else:
                for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    names.add(Path(line.replace("\\", "/")).name)
        except Exception:
            continue
    return {n.lower() for n in names}


def score_path(path: Path, missing: Set[str]) -> Tuple[int, List[str]]:
    reasons: List[str] = []
    score = 0
    name = path.name.lower()
    full = str(path).lower().replace("\\", "/")
    if name in missing:
        score += 25
        reasons.append("missing_filename")
    for tok in NAME_TOKENS:
        if tok in name or tok in full:
            score += 3 if tok in ("realai", "api_server", "embeddings", "orchestr") else 2
            reasons.append(tok)
    if path.suffix.lower() == ".gguf":
        score += 12
        reasons.append("gguf")
    if path.suffix.lower() == ".safetensors" and "adapter" in name:
        score += 10
        reasons.append("lora_adapter")
    if "onedrive/desktop" in full or "onedrive\\desktop" in full:
        score += 4
        reasons.append("onedrive_desktop")
    if "fizz" in full:
        score += 3
        reasons.append("fizz")
    # dedupe reasons
    seen = []
    for r in reasons:
        if r not in seen:
            seen.append(r)
    return score, seen


def walk(root: Path, missing: Set[str], deadline: float) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    n = 0
    if not root.is_dir():
        return hits
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        if time.time() > deadline:
            break
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIR
            and not d.endswith((".dist-info", ".egg-info"))
        ]
        for fn in filenames:
            n += 1
            if n > MAX_WALK_FILES:
                return hits
            if time.time() > deadline:
                return hits
            p = Path(dirpath) / fn
            ext = p.suffix.lower()
            fl = fn.lower()
            # filter: keyword name, missing list, or gold ext under realai-ish path
            interesting = (
                fl in missing
                or any(t in fl for t in NAME_TOKENS)
                or any(t in str(p).lower() for t in ("realai", "agent-tools", "fizz", "openclaw"))
                or ext in {".gguf", ".safetensors"}
            )
            if not interesting:
                continue
            if ext not in STAGE_EXT and fl not in missing:
                # allow .lnk skip, images skip
                if ext in {".lnk", ".url", ".jpg", ".jpeg", ".png", ".mov", ".webp", ".aae"}:
                    continue
            try:
                st = p.stat()
                size = st.st_size
            except OSError:
                continue
            if size > 25 * 1024**3:
                continue
            sc, reasons = score_path(p, missing)
            if sc < 5 and fl not in missing:
                continue
            hits.append({
                "path": win_path(p),
                "posix": str(p),
                "name": p.name,
                "ext": ext,
                "size": size,
                "score": sc,
                "reasons": reasons,
                "root": win_path(root),
                "mtime": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
            })
    return hits


def stage_hits(hits: List[Dict[str, Any]], limit: int = 250) -> List[Dict[str, Any]]:
    _STAGE.mkdir(parents=True, exist_ok=True)
    staged = []
    ordered = sorted(hits, key=lambda h: (-h["score"], -h.get("size", 0)))
    seen_names: Set[str] = set()
    for h in ordered:
        if len(staged) >= limit:
            break
        if h["ext"] not in TEXT_EXT and h["name"].lower() not in {n.lower() for n in P0_NAMES}:
            continue
        if h["size"] > MAX_STAGE_BYTES:
            continue
        src = Path(h["posix"])
        if not src.is_file():
            continue
        # Prefer one best copy per basename (highest score first)
        key = h["name"].lower()
        if key in seen_names and h["score"] < 20:
            continue
        dest_sub = re.sub(r"[^A-Za-z0-9._-]+", "_", h["path"])[-160:]
        dest = _STAGE / dest_sub
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(src, dest)
            staged.append({
                "src": h["path"],
                "dest": win_path(dest),
                "score": h["score"],
                "name": h["name"],
            })
            seen_names.add(key)
        except OSError as e:
            staged.append({"src": h["path"], "error": str(e)})
    return staged


def main() -> int:
    _SCAN.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    missing = load_missing_names()
    roots = [r for r in DEFAULT_ROOTS if r.exists()]
    # ensure OneDrive Desktop first
    roots = sorted(roots, key=lambda p: (0 if "OneDrive/Desktop" in str(p) or "OneDrive\\Desktop" in str(p) else 1, str(p)))

    all_hits: List[Dict[str, Any]] = []
    by_root: Counter = Counter()
    print(f"missing_name_targets={len(missing)} roots={len(roots)}", flush=True)

    for root in roots:
        # OneDrive Desktop gets more budget
        budget = 180 if "Desktop" in str(root) else 90
        deadline = time.time() + budget
        print(f"scan {win_path(root)} budget={budget}s", flush=True)
        hits = walk(root, missing, deadline)
        all_hits.extend(hits)
        by_root[win_path(root)] = len(hits)
        print(f"  hits={len(hits)} total={len(all_hits)}", flush=True)

    # Dedupe by posix path
    uniq: Dict[str, Dict[str, Any]] = {}
    for h in all_hits:
        uniq[h["posix"]] = h
    hits = sorted(uniq.values(), key=lambda h: (-h["score"], h["path"]))

    p0_found = [h for h in hits if h["name"].lower() in {n.lower() for n in P0_NAMES}]
    p0_missing_still = sorted(
        n for n in P0_NAMES
        if not any(h["name"].lower() == n.lower() for h in hits)
    )

    # Compare vs live package presence (filename index, one walk)
    live_index: Dict[str, List[str]] = defaultdict(list)
    if _LIVE.is_dir():
        for dirpath, dirnames, filenames in os.walk(_LIVE):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIR]
            for fn in filenames:
                live_index[fn.lower()].append(str(Path(dirpath) / fn))
    live_have = []
    live_miss = []
    for n in sorted(P0_NAMES):
        matches = (live_index.get(n.lower()) or [])[:3]
        if matches:
            live_have.append({"name": n, "paths": matches})
        else:
            live_miss.append(n)

    staged = stage_hits(hits)

    report = {
        "generated_at": utc(),
        "duration_sec": round(time.time() - t0, 1),
        "mission": "self-heal desktop + local missing-file gold hunt",
        "roots": [win_path(r) for r in roots],
        "hit_count": len(hits),
        "by_root": by_root.most_common(),
        "p0_found_on_desktop_scan": p0_found[:80],
        "p0_still_not_found_anywhere_scanned": p0_missing_still,
        "p0_missing_from_live_realai_pkg": live_miss,
        "p0_present_in_live_realai_pkg": live_have,
        "top_hits": hits[:250],
        "staged_count": len(staged),
        "staged_sample": staged[:50],
        "stage_dir": win_path(_STAGE),
        "onedrive_desktop_note": (
            "C:\\Users\\tsmit\\OneDrive\\Desktop contains a full RealAI-era tree "
            "(realai/, realai - Copy/, realai_agent, plugins, providers, fizzRecovery, .agentx)."
        ),
    }

    (_SCAN / "desktop_missing_gold_map.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (_SCAN / "desktop_missing_gold_paths.txt").write_text(
        "\n".join(f"{h['score']}\t{h['path']}" for h in hits[:3000]),
        encoding="utf-8",
    )

    md = [
        "# Desktop / local missing gold scan",
        "",
        f"Generated: {report['generated_at']}",
        f"Duration: {report['duration_sec']}s",
        f"Hits: {len(hits)}",
        f"Staged: {len(staged)} → `{report['stage_dir']}`",
        "",
        "## OneDrive Desktop",
        "",
        report["onedrive_desktop_note"],
        "",
        "## P0 filenames found on scan",
        "",
    ]
    if not p0_found:
        md.append("_none_")
    for h in p0_found[:40]:
        md.append(f"- **{h['score']}** `{h['name']}` — `{h['path']}`")
    md += ["", "## P0 still missing from live `realai/` package", ""]
    for n in live_miss:
        md.append(f"- `{n}`")
    md += ["", "## Top hits", ""]
    for h in hits[:50]:
        md.append(f"- **{h['score']}** `{h['name']}` — {h['path'][:160]}")
    (_SCAN / "desktop_missing_gold_map.md").write_text("\n".join(md), encoding="utf-8")

    print(json.dumps({
        "ok": True,
        "hits": len(hits),
        "p0_found": len(p0_found),
        "p0_live_miss": live_miss,
        "staged": len(staged),
        "duration": report["duration_sec"],
        "out": str(_SCAN / "desktop_missing_gold_map.json"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
