"""Build pipeline: adapters -> scrub -> length filter -> dedupe -> split -> write (inside REALAI_HOME)."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .adapters import ADAPTERS
from .dedupe import NearDedupe, exact_key
from .scrub import find_secrets, redact

DEFAULTS: Dict[str, Any] = {
    "name": "realai-sft",
    "seed": 42,
    "eval_fraction": 0.1,
    "min_eval_per_source": 1,
    "min_tokens": 8,
    "max_tokens": 1024,
    "near_dup_threshold": 0.85,
    "allow_vendor_chat": False,
    "redact_usernames": [],
    "roots": {},
    "sources": [],
    "tokenizer": None,
}


def realai_home() -> Path:
    env = (os.environ.get("REALAI_HOME") or "").strip()
    return Path(env).expanduser().resolve() if env else Path(__file__).resolve().parents[3]


def _within(path: Path, home: Path) -> bool:
    try:
        path.resolve().relative_to(home.resolve())
        return True
    except ValueError:
        return False


def load_config(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in {".yaml", ".yml"}:
        import yaml  # optional

        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    return {**DEFAULTS, **(data or {})}


class _Tok:
    """Token counter: HF tokenizer when configured and available offline, else ~3.6 chars/token."""

    def __init__(self, name: Optional[str]):
        self.tok = None
        if name:
            try:
                from transformers import AutoTokenizer

                self.tok = AutoTokenizer.from_pretrained(name, local_files_only=True)
            except Exception:
                self.tok = None
        self.kind = "hf:" + str(name) if self.tok else "chars/3.6"

    def count(self, msgs: List[Dict[str, str]]) -> int:
        if self.tok is not None:
            try:
                return len(self.tok.apply_chat_template(msgs, tokenize=True))
            except Exception:
                pass
        return int(sum(len(m["content"]) + 12 for m in msgs) / 3.6) + 1


@dataclass
class BuildResult:
    manifest: Dict[str, Any]
    train: List[Dict[str, Any]] = field(default_factory=list)
    eval: List[Dict[str, Any]] = field(default_factory=list)
    out_dir: Optional[Path] = None


def _row_text(msgs: List[Dict[str, str]]) -> str:
    return "\n".join(f"{m['role']}: {m['content']}" for m in msgs if m["role"] != "system")


def build(cfg: Dict[str, Any], dry_run: bool = False, today: Optional[str] = None) -> BuildResult:
    cfg = {**DEFAULTS, **cfg}
    home = realai_home()
    date = today or _dt.date.today().isoformat()
    out_dir = home / "datasets" / f"{cfg['name']}-{date}"
    if not _within(out_dir, home):
        raise ValueError(f"output {out_dir} is outside REALAI_HOME {home}")

    ctx = {"roots": {k: str(v) for k, v in cfg["roots"].items()}, "allow_vendor_chat": bool(cfg["allow_vendor_chat"])}
    tok = _Tok(cfg.get("tokenizer"))
    stats: Dict[str, Counter] = defaultdict(Counter)
    secret_kinds: Counter = Counter()
    exact_seen: set = set()
    near = NearDedupe(threshold=float(cfg["near_dup_threshold"]))
    kept: List[Dict[str, Any]] = []

    for spec in cfg["sources"]:
        name = spec.get("name") or spec["type"]
        st = stats[name]
        if spec.get("enabled", True) is False:
            st["disabled"] += 1
            continue
        if spec["type"] == "ide_chat" and not ctx["allow_vendor_chat"]:
            st["excluded_vendor_chat"] += 1
            continue
        fn = ADAPTERS.get(spec["type"])
        if fn is None:
            raise ValueError(f"unknown adapter type {spec['type']!r}")
        try:
            rows = list(fn(spec, ctx))
        except Exception as exc:  # one bad source must not kill the build
            st["error"] += 1
            st["error_msg:" + type(exc).__name__ + ": " + str(exc)[:120]] += 1
            continue
        for drop in ctx.pop("_gate_drops", []):
            st["dropped_quality_gate"] += 1
        for row in rows:
            st["read"] += 1
            msgs = row["messages"]
            raw = "\n".join(m["content"] for m in msgs)
            hits = find_secrets(raw)
            if hits:
                st["dropped_secret"] += 1
                secret_kinds.update(hits)
                continue
            msgs = [{"role": m["role"], "content": redact(m["content"], cfg["redact_usernames"])} for m in msgs]
            n_tok = tok.count(msgs)
            if n_tok < int(cfg["min_tokens"]):
                st["dropped_short"] += 1
                continue
            if n_tok > int(cfg["max_tokens"]):
                st["dropped_long"] += 1
                continue
            text = _row_text(msgs)
            key = exact_key(text)
            if key in exact_seen:
                st["dropped_exact_dup"] += 1
                continue
            exact_seen.add(key)
            if not near.add_if_new(text):
                st["dropped_near_dup"] += 1
                continue
            st["kept"] += 1
            kept.append({
                "messages": msgs,
                "source": name,
                "license": spec.get("license", "unknown"),
                "origin": spec.get("origin", ""),
                "tokens_est": n_tok,
                "id": key[:16],
                "meta": {k: v for k, v in (row.get("meta") or {}).items() if v is not None},
            })

    # Stratified split by source, fixed seed, stable order (sort by id first).
    rng = random.Random(int(cfg["seed"]))
    by_src: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in sorted(kept, key=lambda r: (r["source"], r["id"])):
        by_src[r["source"]].append(r)
    train, ev = [], []
    for src in sorted(by_src):
        rows = by_src[src][:]
        rng.shuffle(rows)
        n_eval = int(round(len(rows) * float(cfg["eval_fraction"])))
        if len(rows) >= 10:
            n_eval = max(n_eval, int(cfg["min_eval_per_source"]))
        ev += rows[:n_eval]
        train += rows[n_eval:]
        stats[src]["train"] = len(rows) - n_eval
        stats[src]["eval"] = n_eval

    def _blob(rows):
        return "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)

    train_s, eval_s = _blob(train), _blob(ev)
    manifest = {
        "name": cfg["name"],
        "date": date,
        "format": "qwen-chat messages (role/content); apply tokenizer.apply_chat_template at train time",
        "out_dir": str(out_dir),
        "dry_run": dry_run,
        "seed": cfg["seed"],
        "eval_fraction": cfg["eval_fraction"],
        "token_counter": tok.kind,
        "token_window": [cfg["min_tokens"], cfg["max_tokens"]],
        "near_dup_threshold": cfg["near_dup_threshold"],
        "allow_vendor_chat": ctx["allow_vendor_chat"],
        "totals": {
            "kept": len(kept),
            "train": len(train),
            "eval": len(ev),
            "read": sum(s["read"] for s in stats.values()),
            "dropped_exact_dup": sum(s["dropped_exact_dup"] for s in stats.values()),
            "dropped_near_dup": sum(s["dropped_near_dup"] for s in stats.values()),
            "dropped_secret": sum(s["dropped_secret"] for s in stats.values()),
            "dropped_long": sum(s["dropped_long"] for s in stats.values()),
            "dropped_short": sum(s["dropped_short"] for s in stats.values()),
            "dropped_quality_gate": sum(s["dropped_quality_gate"] for s in stats.values()),
        },
        "secret_kinds_dropped": dict(secret_kinds),
        "sources": {k: dict(v) for k, v in stats.items()},
        "licenses": dict(Counter(r["license"] for r in kept)),
        "sha256": {
            "train.jsonl": hashlib.sha256(train_s.encode("utf-8")).hexdigest(),
            "eval.jsonl": hashlib.sha256(eval_s.encode("utf-8")).hexdigest(),
        },
    }
    res = BuildResult(manifest=manifest, train=train, eval=ev, out_dir=out_dir)
    if dry_run:
        return res
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "train.jsonl").write_text(train_s, encoding="utf-8")
    (out_dir / "eval.jsonl").write_text(eval_s, encoding="utf-8")
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return res
