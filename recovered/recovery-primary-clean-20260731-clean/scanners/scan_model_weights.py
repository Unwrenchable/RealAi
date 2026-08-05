#!/usr/bin/env python3
"""
RealAI Model Weights Gold Scanner
=================================
Find local (and optional remote-path-hint) model weight files for connection
into RealAI / Vulkan / local_models registry.

Discovers: .gguf .ggml .safetensors .bin (hf) .onnx .pt/.pth (optional)
Skips pure noise: node_modules, venv site-packages bulk, etc.

Outputs:
  scan_results/weights_gold_map.json
  scan_results/weights_gold_map.md
  scan_results/weights_connect_candidates.json  (ready for registry)

Also merges weight paths into era_map-style external list for deepen mining.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

ROOT = Path(os.environ.get("REALAI_ROOT", r"C:\realai"))
if not ROOT.exists():
    ROOT = Path("/mnt/c/realai")
OUT_DIR = ROOT / "scan_results"
OUT_JSON = OUT_DIR / "weights_gold_map.json"
OUT_MD = OUT_DIR / "weights_gold_map.md"
OUT_CONNECT = OUT_DIR / "weights_connect_candidates.json"

WEIGHT_EXTS = {
    ".gguf",
    ".ggml",
    ".safetensors",
    ".onnx",
    # heavy / optional — still record if under model dirs
    ".pt",
    ".pth",
    ".bin",  # often HF shards; filtered by path heuristics
}

SKIP_DIR_NAMES = {
    "node_modules", ".git", "venv", ".venv", "env", "__pycache__",
    ".pytest_cache", ".mypy_cache", "site-packages", "dist", "build",
    ".next", ".vs", "scan_results", "terminals", "chocolatey",
    "phase4_tools", "plan_phase4_preview",
}

# Prefer these roots (fast + high yield)
DEFAULT_ROOTS: List[str] = [
    str(ROOT / "models"),
    r"C:\llama-vulkan\models",
    r"C:\llama-vulkan",
    r"C:\llama\models",
    r"C:\models",
    r"C:\Users\tsmit\.realai\models",
    r"C:\Users\tsmit\.realai",
    r"C:\Users\tsmit\models",
    r"C:\Users\tsmit\realai\models",
    r"C:\Users\tsmit\realai-clean\models",
    r"C:\Users\tsmit\.cache\huggingface\hub",
    r"C:\Users\tsmit\.cache\huggingface",
    r"C:\Users\tsmit\.lmstudio\models",
    r"C:\Users\tsmit\.lmstudio",
    r"C:\Users\tsmit\.ollama\models",
    r"C:\Users\tsmit\AppData\Local\llama.cpp",
    r"C:\Users\tsmit\AppData\Roaming\llama.cpp",
    r"C:\Users\tsmit\OneDrive\Desktop",
    r"C:\Users\tsmit\Downloads",
    r"C:\Users\tsmit\Documents",
    r"C:\Users\tsmit\Meta-Llama-3-70B-Instruct",
    r"C:\realai\recovered",
    r"C:\llama-vulkan\models\realai-1.0",
    r"C:\llama-vulkan\models\realai-overseer",
]

# Soft max walk depth per root (None = unlimited under model-ish roots)
MAX_DEPTH_DEFAULT = 6
MAX_FILES_HARD = 5000


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_win(p: Path) -> str:
    s = str(p)
    if s.startswith("/mnt/c/"):
        return "C:\\" + s[7:].replace("/", "\\")
    return s


def resolve_root(s: str) -> Optional[Path]:
    p = Path(s)
    if p.exists():
        return p
    if s.startswith("C:\\") or s.startswith("C:/"):
        wsl = Path("/mnt/c/" + s[3:].replace("\\", "/"))
        if wsl.exists():
            return wsl
    return None


def should_skip_dir(name: str) -> bool:
    low = name.lower()
    if low in SKIP_DIR_NAMES:
        return True
    if low.endswith(".egg-info"):
        return True
    return False


def classify_weight(path: Path, size: int) -> Dict[str, Any]:
    name = path.name.lower()
    ext = path.suffix.lower()
    tags: List[str] = []
    family = "unknown"
    role = "weight"
    connectable = False

    if ext == ".gguf":
        tags.append("gguf")
        connectable = True
        role = "gguf_chat"
        if "embed" in name:
            role = "gguf_embed"
            tags.append("embedding")
        if "overseer" in name:
            tags.append("overseer")
        if "realai" in name:  # filename only — not parent path C:\realai\...
            family = "realai"
            tags.append("realai_family")
        elif "qwen" in name:
            family = "qwen"
        elif "llama" in name or "meta-llama" in name:
            family = "llama"
        elif "mistral" in name or "mixtral" in name:
            family = "mistral"
        elif "phi" in name:
            family = "phi"
        elif "gemma" in name:
            family = "gemma"
        # quant hint
        for q in ("q2", "q3", "q4", "q5", "q6", "q8", "f16", "f32", "iq"):
            if q in name:
                tags.append(f"quant_{q}")
                break
    elif ext == ".safetensors":
        tags.append("safetensors")
        family = "hf"
        role = "hf_shard"
        connectable = size > 10_000_000  # real weight shard
        if "embed" in name or "sentence" in str(path).lower():
            tags.append("embedding")
    elif ext in (".pt", ".pth"):
        tags.append("pytorch")
        role = "torch_checkpoint"
        connectable = False  # needs convert for vulkan
    elif ext == ".onnx":
        tags.append("onnx")
        role = "onnx"
        connectable = True
    elif ext == ".bin":
        # HF pytorch_model.bin or ggml
        if "pytorch" in name or "model" in name or "adapter" in name:
            tags.append("hf_bin")
            role = "hf_bin"
            family = "hf"
            connectable = size > 50_000_000
        else:
            tags.append("bin_other")
            connectable = False
    elif ext == ".ggml":
        tags.append("ggml")
        role = "ggml_legacy"
        connectable = True

    # size class
    if size >= 4_000_000_000:
        tags.append("size_xl")
    elif size >= 1_000_000_000:
        tags.append("size_l")
    elif size >= 100_000_000:
        tags.append("size_m")
    else:
        tags.append("size_s")

    # live default detection
    live_default = "qwen2.5-coder-7b-instruct-q5_k_m.gguf" in name

    return {
        "family": family,
        "role": role,
        "tags": tags,
        "connectable_gguf_or_engine": connectable and ext in (".gguf", ".ggml", ".onnx"),
        "connectable_note": (
            "Ready for llama-server -m path" if ext == ".gguf"
            else "Needs conversion/training export for Vulkan" if ext in (".safetensors", ".pt", ".pth", ".bin")
            else "Engine-specific"
        ),
        "is_live_default": live_default,
        # Filename only — avoid marking everything under C:\realai as realai-named
        "is_realai_named": "realai" in name,
    }


def walk_weights(root: Path, max_depth: int, max_files: int) -> Iterable[Path]:
    root = root.resolve()
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # depth
        try:
            rel = Path(dirpath).relative_to(root)
            depth = len(rel.parts)
        except ValueError:
            depth = 0
        if depth >= max_depth:
            dirnames[:] = []
        else:
            dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]

        for fn in filenames:
            ext = Path(fn).suffix.lower()
            if ext not in WEIGHT_EXTS:
                continue
            # skip tiny bin junk / lock-ish
            full = Path(dirpath) / fn
            try:
                sz = full.stat().st_size
            except OSError:
                continue
            if ext == ".bin" and sz < 1_000_000:
                continue
            if ext in (".pt", ".pth") and sz < 100_000:
                continue
            yield full
            count += 1
            if count >= max_files:
                return


def file_fingerprint(path: Path, size: int) -> Optional[str]:
    """Partial hash for dedupe (first+last 1MB) — fast for multi-GB."""
    try:
        h = hashlib.md5()
        with path.open("rb") as f:
            head = f.read(1_048_576)
            h.update(head)
            if size > 2_097_152:
                f.seek(max(0, size - 1_048_576))
                h.update(f.read(1_048_576))
            h.update(str(size).encode())
        return h.hexdigest()
    except Exception:
        return None


def scan(roots: List[str], max_depth: int = MAX_DEPTH_DEFAULT) -> Dict[str, Any]:
    started = utc()
    t0 = time.time()
    hits: List[Dict[str, Any]] = []
    by_hash: Dict[str, List[str]] = defaultdict(list)
    errors: List[str] = []
    roots_ok: List[str] = []
    roots_miss: List[str] = []

    for rs in roots:
        rp = resolve_root(rs)
        if rp is None:
            roots_miss.append(rs)
            continue
        roots_ok.append(to_win(rp) if rp.exists() else rs)
        try:
            for full in walk_weights(rp, max_depth=max_depth, max_files=MAX_FILES_HARD):
                try:
                    st = full.stat()
                    size = st.st_size
                except OSError as e:
                    errors.append(f"{full}: {e}")
                    continue
                meta = classify_weight(full, size)
                fp = file_fingerprint(full, size) if size < 20_000_000_000 else None
                win = to_win(full)
                if fp:
                    by_hash[fp].append(win)
                hits.append({
                    "path": win,
                    "name": full.name,
                    "size": size,
                    "size_gb": round(size / (1024 ** 3), 3),
                    "mtime": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                    "ext": full.suffix.lower(),
                    "fingerprint": fp,
                    **meta,
                })
        except PermissionError as e:
            errors.append(f"{rs}: {e}")
        except Exception as e:
            errors.append(f"{rs}: {e}")

    # Dedupe groups
    unique_by_fp: Dict[str, Dict[str, Any]] = {}
    no_fp: List[Dict[str, Any]] = []
    for h in hits:
        fp = h.get("fingerprint")
        if not fp:
            no_fp.append(h)
            continue
        if fp not in unique_by_fp:
            unique_by_fp[fp] = {**h, "copies": [h["path"]]}
        else:
            unique_by_fp[fp]["copies"].append(h["path"])

    uniques = list(unique_by_fp.values()) + [{**h, "copies": [h["path"]]} for h in no_fp]

    # Connect candidates for Vulkan / RealAI
    # Prefer realai-named path when multiple hardlinks share a fingerprint
    connect = []
    for u in uniques:
        if u.get("ext") != ".gguf" or u.get("size", 0) <= 50_000_000:
            continue
        copies = u.get("copies") or [u["path"]]
        # pick best path: realai-named file, then under C:\realai\models, then first
        def path_score(p: str) -> tuple:
            name = Path(p).name.lower()
            score = 0
            if "realai" in name:
                score += 100
            if "\\realai\\models\\" in p.lower() or "/realai/models/" in p.lower():
                score += 50
            if "qwen" in name and "coder" in name:
                score += 40
            if "overseer" in p.lower():
                score += 20
            if "recycle" in p.lower() or "extracted" in p.lower():
                score -= 30  # prefer non-truncated restore copies
            return (score, -len(p))

        best = sorted(copies, key=path_score, reverse=True)[0]
        best_name = Path(best).name
        is_realai = "realai" in best_name.lower()
        is_live = "qwen2.5-coder-7b-instruct-q5_k_m.gguf" in best_name.lower()
        # incomplete recycle copy if same name but much smaller than full
        full_qwen = 5.0
        incomplete = (
            "qwen2.5-coder" in best_name.lower()
            and float(u.get("size_gb") or 0) < full_qwen * 0.9
        )
        connect.append({
            "id": re.sub(r"[^a-zA-Z0-9_.-]+", "-", best_name).lower(),
            "name": best_name,
            "path": best,
            "size_gb": u["size_gb"],
            "family": "realai" if is_realai else u.get("family"),
            "role": u.get("role"),
            "is_live_default": is_live and not incomplete,
            "is_realai_named": is_realai,
            "incomplete_copy": incomplete,
            "copies": copies,
            "copy_count": len(copies),
            "vulkan_cmd": (
                f'llama-server.exe -m "{best}" --host 127.0.0.1 --port 8080 '
                f"-c 8192 -ngl 99 --jinja"
            ),
            "realai_model_id_suggestion": (
                "realai-default-coder" if is_live and not incomplete
                else ("realai-1.0-instruct" if is_realai
                      else f"local-{u.get('family', 'model')}")
            ),
        })

    connect.sort(key=lambda x: (-(1 if x.get("is_live_default") else 0),
                                -(1 if x.get("is_realai_named") else 0),
                                -float(x.get("size_gb") or 0)))

    # Stats
    by_family = defaultdict(int)
    by_ext = defaultdict(int)
    total_bytes = 0
    for h in hits:
        by_family[h.get("family") or "unknown"] += 1
        by_ext[h.get("ext") or "?"] += 1
        total_bytes += int(h.get("size") or 0)

    report = {
        "meta": {
            "generated_at": utc(),
            "elapsed_seconds": round(time.time() - t0, 2),
            "root_authority": str(ROOT),
            "purpose": "Find local model weights gold for RealAI connect / registry",
        },
        "roots_scanned": roots_ok,
        "roots_missing": roots_miss,
        "stats": {
            "files_found": len(hits),
            "unique_fingerprints": len(uniques),
            "connectable_gguf": len(connect),
            "total_bytes": total_bytes,
            "total_gb": round(total_bytes / (1024 ** 3), 2),
            "by_family": dict(by_family),
            "by_ext": dict(by_ext),
        },
        "weights": hits,
        "uniques": uniques,
        "connect_candidates": connect,
        "errors": errors[:50],
    }
    return report


def write_reports(report: Dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    OUT_CONNECT.write_text(
        json.dumps({
            "generated_at": report["meta"]["generated_at"],
            "candidates": report.get("connect_candidates") or [],
            "how_to_connect": {
                "vulkan": "Point llama-server -m at path",
                "orchestrator": "Set REALAI_DEFAULT_MODEL and REALAI_VULKAN_BASE",
                "provider_facade_todo": "Map realai-* ids to these paths in /v1/models",
            },
        }, indent=2),
        encoding="utf-8",
    )

    st = report["stats"]
    lines = [
        "# RealAI Weights Gold Map",
        "",
        f"Generated: `{report['meta']['generated_at']}`",
        "",
        f"**Found:** {st['files_found']} weight files · **unique:** {st['unique_fingerprints']} · "
        f"**connectable GGUF:** {st['connectable_gguf']} · **total ~{st['total_gb']} GB**",
        "",
        "## By family",
        "",
    ]
    for k, v in sorted((st.get("by_family") or {}).items(), key=lambda x: -x[1]):
        lines.append(f"- `{k}`: {v}")
    lines += ["", "## Connect candidates (GGUF → Vulkan / RealAI)", ""]
    for c in (report.get("connect_candidates") or [])[:40]:
        flag = []
        if c.get("is_live_default"):
            flag.append("**LIVE DEFAULT**")
        if c.get("is_realai_named"):
            flag.append("**realai-named**")
        flags = " ".join(flag)
        lines.append(
            f"- `{c['realai_model_id_suggestion']}` — `{c['name']}` "
            f"({c['size_gb']} GB) {flags}"
        )
        lines.append(f"  - path: `{c['path']}`")
        if c.get("copies") and len(c["copies"]) > 1:
            lines.append(f"  - copies: {len(c['copies'])}")
    lines += [
        "",
        "## Roots scanned",
        "",
    ]
    for r in report.get("roots_scanned") or []:
        lines.append(f"- OK `{r}`")
    if report.get("roots_missing"):
        lines += ["", "## Roots not found", ""]
        for r in report["roots_missing"][:30]:
            lines.append(f"- miss `{r}`")
    lines += [
        "",
        "## Next",
        "",
        "1. Pick a connect candidate GGUF",
        "2. Restart Vulkan with that `-m` path",
        "3. Or register under RealAI model id facade on orchestrator",
        "",
        f"JSON: `{OUT_JSON}`",
        f"Connect list: `{OUT_CONNECT}`",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Scan machine for model weights gold")
    ap.add_argument("--root", action="append", help="Extra root to scan (repeatable)")
    ap.add_argument("--max-depth", type=int, default=MAX_DEPTH_DEFAULT)
    ap.add_argument("--deep", action="store_true", help="Also scan C:\\Users\\tsmit shallow extra")
    args = ap.parse_args()

    roots = list(DEFAULT_ROOTS)
    if args.root:
        roots.extend(args.root)
    if args.deep:
        roots.append(r"C:\Users\tsmit")

    # de-dupe preserve order
    seen: Set[str] = set()
    uniq_roots = []
    for r in roots:
        k = r.lower()
        if k not in seen:
            seen.add(k)
            uniq_roots.append(r)

    print(f"[weights] scanning {len(uniq_roots)} roots...")
    report = scan(uniq_roots, max_depth=args.max_depth)
    write_reports(report)
    st = report["stats"]
    print(f"[weights] files={st['files_found']} unique={st['unique_fingerprints']} "
          f"gguf_connect={st['connectable_gguf']} total_gb={st['total_gb']}")
    print(f"[weights] -> {OUT_JSON}")
    print(f"[weights] -> {OUT_MD}")
    print(f"[weights] -> {OUT_CONNECT}")
    print("[weights] top connect candidates:")
    for c in (report.get("connect_candidates") or [])[:12]:
        print(f"  - {c['name']}  {c['size_gb']}GB  {c['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
