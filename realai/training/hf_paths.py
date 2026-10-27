"""Resolve model paths: plain HF model dirs, HF cache repo dirs (models--org--name), or hub ids.

    resolve_model_path("D:/hf_cache/models--Qwen--Qwen2.5-3B-Instruct")
      -> D:/hf_cache/models--Qwen--Qwen2.5-3B-Instruct/snapshots/<refs/main or newest complete snapshot>
"""
from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any, Dict, List, Union

WEIGHT_SUFFIXES = (".safetensors", ".bin")


def _has_config(p: Path) -> bool:
    return (p / "config.json").is_file()


def resolve_model_path(p: Union[str, Path]) -> str:
    s = str(p)
    q = Path(s)
    if not q.exists():
        return s  # hub id or not-yet-present path: leave to transformers
    if _has_config(q):
        return str(q)
    root = q if (q / "snapshots").is_dir() else (q.parent.parent if q.parent.name == "snapshots" else None)
    if root is None:
        sub = sorted(d for d in q.glob("models--*") if (d / "snapshots").is_dir())  # a whole hub cache dir
        if len(sub) == 1:
            root = sub[0]
    if root is None:
        return s
    ref = root / "refs" / "main"
    if ref.is_file():
        snap = root / "snapshots" / ref.read_text(encoding="utf-8").strip()
        if _has_config(snap):
            return str(snap)
    snaps = sorted((d for d in (root / "snapshots").iterdir() if _has_config(d)), key=lambda d: d.stat().st_mtime)
    if not snaps:
        raise FileNotFoundError(f"no snapshot with config.json under {root}")
    return str(snaps[-1])


def safetensors_ok(f: Path) -> str:
    """'OK' if the header parses and file size == 8 + header + last tensor offset."""
    try:
        n = f.stat().st_size
        with f.open("rb") as fh:
            hl = struct.unpack("<Q", fh.read(8))[0]
            if hl > 100_000_000:
                return "BAD header length"
            h = json.loads(fh.read(hl))
        end = max((v["data_offsets"][1] for k, v in h.items() if k != "__metadata__"), default=0)
        need = 8 + hl + end
        return "OK" if n == need else (f"TRUNCATED {n}/{need}" if n < need else f"EXTRA {n - need}B")
    except Exception as exc:
        return f"BAD {type(exc).__name__}"


def check_model_dir(p: Union[str, Path]) -> Dict[str, Any]:
    """Completeness of an HF model dir: config, tokenizer, every shard in the index present and intact."""
    d = Path(resolve_model_path(p))
    out: Dict[str, Any] = {"path": str(d), "problems": []}
    for need in ("config.json", "tokenizer_config.json"):
        if not (d / need).is_file():
            out["problems"].append(f"missing {need}")
    if not ((d / "tokenizer.json").is_file() or (d / "vocab.json").is_file()):
        out["problems"].append("missing tokenizer.json/vocab.json")
    idx = d / "model.safetensors.index.json"
    shards: List[str] = sorted(set(json.loads(idx.read_text(encoding="utf-8"))["weight_map"].values())) if idx.is_file() \
        else [f.name for f in d.glob("*.safetensors")]
    if not shards:
        out["problems"].append("no safetensors weights")
    out["shards"] = {}
    for s in shards:
        f = d / s
        st = safetensors_ok(f) if f.is_file() else "MISSING"
        out["shards"][s] = st
        if st != "OK":
            out["problems"].append(f"{s}: {st}")
    out["size_gb"] = round(sum((d / s).stat().st_size for s in shards if (d / s).is_file()) / 1e9, 2)
    out["ok"] = not out["problems"]
    return out


if __name__ == "__main__":
    import sys

    r = check_model_dir(sys.argv[1])
    print(json.dumps(r, indent=1))
    raise SystemExit(0 if r["ok"] else 1)
