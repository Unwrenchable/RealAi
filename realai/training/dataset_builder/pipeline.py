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

    def count(self, msgs: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> int:
        if self.tok is not None:
            try:
                r = self.tok.apply_chat_template(msgs, tools=tools or None, tokenize=True)
                return len(r["input_ids"] if hasattr(r, "keys") else r)
            except Exception:
                pass
        extra = len(json.dumps(tools)) + 200 if tools else 0
        return int((sum(len(_msg_text(m)) + 12 for m in msgs) + extra) / 3.6) + 1


@dataclass
class BuildResult:
    manifest: Dict[str, Any]
    train: List[Dict[str, Any]] = field(default_factory=list)
    eval: List[Dict[str, Any]] = field(default_factory=list)
    out_dir: Optional[Path] = None
    attribution: str = ""


def _msg_text(m: Dict[str, Any]) -> str:
    """content plus serialized tool calls (tool-call rows have empty content on the calling turn)."""
    t = str(m.get("content") or "")
    if m.get("tool_calls"):
        t += json.dumps(m["tool_calls"], ensure_ascii=False, sort_keys=True)
    return t


def _row_text(msgs: List[Dict[str, Any]]) -> str:
    return "\n".join(f"{m['role']}: {_msg_text(m)}" for m in msgs if m["role"] != "system")


def _redact_msg(m: Dict[str, Any], users: List[str]) -> Dict[str, Any]:
    out = {"role": m["role"], "content": redact(str(m.get("content") or ""), users)}
    if m.get("tool_calls"):
        out["tool_calls"] = json.loads(redact(json.dumps(m["tool_calls"], ensure_ascii=False), users))
    if m.get("name"):
        out["name"] = m["name"]
    return out


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
            raw = "\n".join(_msg_text(m) for m in msgs)
            hits = find_secrets(raw)
            if hits:
                st["dropped_secret"] += 1
                secret_kinds.update(hits)
                continue
            msgs = [_redact_msg(m, cfg["redact_usernames"]) for m in msgs]
            tools = row.get("tools")
            n_tok = tok.count(msgs, tools)
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
            if spec.get("near_dedupe", True) and not near.add_if_new(text):
                st["dropped_near_dup"] += 1
                continue
            st["kept"] += 1
            kept.append({
                "messages": msgs,
                **({"tools": tools} if tools else {}),
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
        "format": "qwen-chat messages (role/content; assistant tool_calls + role=tool for tool rows, row.tools = specs); apply tokenizer.apply_chat_template(messages, tools=row.tools) at train time",
        "kinds": dict(Counter("tool_call" if r.get("tools") else "plain" for r in kept)),
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
    attribution = attribution_text(cfg, stats)
    manifest["attribution_sha256"] = hashlib.sha256(attribution.encode("utf-8")).hexdigest()
    res = BuildResult(manifest=manifest, train=train, eval=ev, out_dir=out_dir)
    res.attribution = attribution
    if dry_run:
        return res
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "train.jsonl").write_bytes(train_s.encode("utf-8"))  # LF on Windows too: hashes match
    (out_dir / "eval.jsonl").write_bytes(eval_s.encode("utf-8"))
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "ATTRIBUTION.md").write_text(attribution, encoding="utf-8")
    return res


_REPO_ROOT = Path(__file__).resolve().parents[3]


def attribution_text(cfg: Dict[str, Any], stats: Dict[str, Any]) -> str:
    """Per-source licence/origin; third-party sources carry their licence text (MIT etc. require it)."""
    out = [f"# Attribution for dataset {cfg['name']}", "",
           "| source | rows kept | licence | origin |", "|---|---|---|---|"]
    third = []
    for spec in cfg.get("sources", []):
        name = spec.get("name")
        kept = (stats.get(name) or {}).get("kept", 0)
        if not kept:
            continue
        out.append(f"| {name} | {kept} | {spec.get('license', 'unknown')} | {spec.get('origin', '')} |")
        if spec.get("license_file"):
            third.append(spec)
    for spec in third:
        lf = Path(spec["license_file"])
        lf = lf if lf.is_absolute() else _REPO_ROOT / lf
        out += ["", f"## {spec['name']}", "", spec.get("attribution", ""), ""]
        out.append("```\n" + (lf.read_text(encoding="utf-8").strip() if lf.is_file() else f"MISSING licence file {lf}") + "\n```")
    return "\n".join(out) + "\n"
