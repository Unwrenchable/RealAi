"""Auto model ledger: MODELS.md (human) + models_ledger.json (machine).

Written only by code (train_sft train/export/register, spotcheck, self_data improve, `seed`).
Never edit by hand: every write re-renders MODELS.md from the JSON. Updates are idempotent
(an update that changes nothing writes no history entry); every real change appends to history.

Paths: REALAI_MODELS_LEDGER=<path to MODELS.md> (json sits next to it), else
<REALAI_MODELS_ROOT or C:\\models (Windows) / ~/models>/MODELS.md.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

SECTIONS = ("runs", "baselines", "archived", "bases")
TITLES = {"runs": "Trained runs", "baselines": "Exported baselines (GGUF)", "archived": "Archived experiments",
          "bases": "Base models available"}


def models_root() -> Path:
    r = os.environ.get("REALAI_MODELS_ROOT")
    if r:
        return Path(r)
    return Path("C:/models") if os.name == "nt" else Path.home() / "models"


def md_path() -> Path:
    p = os.environ.get("REALAI_MODELS_LEDGER")
    return Path(p) if p else models_root() / "MODELS.md"


def json_path() -> Path:
    return md_path().with_name("models_ledger.json")


def _now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def load() -> Dict[str, Any]:
    p = json_path()
    d = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
    d.setdefault("version", 1)
    for s in SECTIONS:
        d.setdefault(s, {})
    d.setdefault("next", [])
    d.setdefault("history", [])
    return d


def _merge(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-merge src into dst; return the subset of src that actually changed."""
    changed: Dict[str, Any] = {}
    for k, v in src.items():
        if v is None:
            continue
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            sub = _merge(dst[k], v)
            if sub:
                changed[k] = sub
        elif dst.get(k) != v:
            dst[k] = v
            changed[k] = v
    return changed


def save(d: Dict[str, Any]) -> Path:
    jp = json_path()
    jp.parent.mkdir(parents=True, exist_ok=True)
    tmp = jp.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, jp)
    md_path().write_text(render(d), encoding="utf-8")
    return jp


def update(section: str, key: str, event: str, fields: Dict[str, Any], d: Optional[Dict[str, Any]] = None) -> bool:
    """Merge fields into d[section][key]; append history only if something changed. Returns changed."""
    own = d is None
    d = load() if own else d
    ent = d[section].setdefault(key, {})
    fresh = not ent
    changed = _merge(ent, fields)
    if fresh or changed:
        ent["updated"] = _now()
        d["history"].append({"ts": ent["updated"], "event": event, "section": section, "id": key, "changed": changed})
    if own and (fresh or changed):
        save(d)
    return bool(fresh or changed)


def set_next(items, d: Optional[Dict[str, Any]] = None) -> None:
    own = d is None
    d = load() if own else d
    if d["next"] != list(items):
        d["next"] = list(items)
        d["history"].append({"ts": _now(), "event": "next", "section": "next", "id": "-", "changed": list(items)})
        if own:
            save(d)


def safe(fn, *a, **kw):
    """Ledger hooks must never break training/export/spotcheck."""
    try:
        return fn(*a, **kw)
    except Exception as exc:  # pragma: no cover - best effort
        print(f"[ledger] skipped: {type(exc).__name__}: {exc}", file=sys.stderr)
        return None


# ----------------------------------------------------------------------------- hooks
def run_id(out: Path) -> str:
    n = Path(out).name
    return n[4:] if n.startswith("sft-") else n


def on_train(out: Path, res: Dict[str, Any], started: Optional[str] = None, model_id: Optional[str] = None) -> bool:
    out = Path(out)
    ds = res.get("dataset") or {}
    mix = None
    mp = Path(ds.get("dir", "")) / "manifest.json" if ds.get("dir") else None
    if mp and mp.is_file():
        m = json.loads(mp.read_text(encoding="utf-8"))
        mix = {k: v.get("kept") for k, v in (m.get("sources") or {}).items() if isinstance(v, dict) and v.get("kept")}
    hist = res.get("history") or []
    f = {"run": out.name, "run_dir": str(out), "model_id": model_id, "status": "trained",
         "base_model": (res.get("recipe") or {}).get("base_model"),
         "dataset": {"name": ds.get("manifest_name"), "dir": ds.get("dir"), "train_rows": ds.get("train"),
                     "eval_rows": ds.get("eval"), "manifest_sha256": ds.get("manifest_sha256"), "source_mix": mix},
         "steps": res.get("steps"), "sec_per_step": round(res["sec_per_step"], 2) if res.get("sec_per_step") else None,
         "eval_loss_per_epoch": {str(h["epoch"]): round(h["eval_loss"], 4) for h in hist if "eval_loss" in h},
         "best_eval_loss": round(res["best_eval_loss"], 4) if res.get("best_eval_loss") is not None else None,
         "adapter": str(out / "adapter_best"), "started": started,
         "finished": res.get("finished") or _dt.datetime.fromtimestamp((out / "train_result.json").stat().st_mtime).astimezone().isoformat(timespec="seconds")
         if (out / "train_result.json").is_file() else _now()}
    return update("runs", run_id(out), "train", f)


def on_eval(out: Path, rep: Dict[str, Any]) -> bool:
    return update("runs", run_id(out), "eval", {"base_eval_loss": round(rep["base_eval_loss"], 4),
                                                "eval_passed": rep.get("passed")})


def on_export(out: Path, gguf: Path, quant: str, model_id: str, sha256: Optional[str] = None) -> bool:
    g = Path(gguf)
    return update("runs", run_id(out), "export", {
        "model_id": model_id, "status": "exported",
        "gguf": {quant: {"path": str(g), "size_gb": round(g.stat().st_size / 1e9, 3) if g.is_file() else None, "sha256": sha256}}})


def on_spotcheck(rep: Dict[str, Any], report: Path, model_id: str) -> bool:
    if not model_id:
        return False
    d = load()
    mode = "tools" if rep.get("use_tools", True) else "no_tools"
    sec = next((s for s in ("runs", "baselines") if any(k == model_id or v.get("model_id") == model_id for k, v in d[s].items())), "baselines")
    key = next((k for k, v in d[sec].items() if k == model_id or v.get("model_id") == model_id), model_id)
    f = {"spotcheck": {mode: {"passed": rep.get("passed"), "n": rep.get("n"), "pass_rate": rep.get("pass_rate"),
                              "date": rep.get("ts"), "report": str(report)}}}
    ch = update(sec, key, "spotcheck", f, d)
    if ch:
        save(d)
    return ch


def on_register(out: Path, entry: Dict[str, Any]) -> bool:
    return update("runs", run_id(out), "register", {
        "model_id": entry.get("id"), "registered": entry.get("registered_at"), "default": bool(entry.get("default")),
        "status": "registered-default" if entry.get("default") else "registered"})


def on_improve(rep: Dict[str, Any], report: Optional[Path] = None) -> bool:
    return update("runs", "_self_data", "improve", {
        "status": "data-loop", "selfplay_rows_added_recent": rep.get("selfplay_rows_added_recent"),
        "last_improve": rep.get("ts"), "report": str(report) if report else None,
        "weak_tools": [w["tool"] for w in rep.get("weak", [])][:8]})


# ----------------------------------------------------------------------------- render
def _sc(e: Dict[str, Any]) -> str:
    sc = e.get("spotcheck") or {}
    out = []
    for m in ("tools", "no_tools"):
        if m in sc:
            out.append(f"{m.replace('_', '-')} {sc[m]['passed']}/{sc[m]['n']} ({str(sc[m].get('date', ''))[:10]})")
    return "; ".join(out) or "-"


def render(d: Dict[str, Any]) -> str:
    L = ["# RealAI model ledger", "",
         "> Auto-generated by `realai.training.ledger` from `models_ledger.json`. **Do not edit by hand**; ",
         "> changes come from train_sft train/eval/export/register, spotcheck, self_data improve, or `python -m realai.training.ledger seed`.",
         f"> Last write: {_now()}", ""]
    runs = d["runs"]
    L += [f"## {TITLES['runs']}", "",
          "| run | model id | status | base | dataset (train/eval) | steps | eval loss by epoch | best | spotcheck | gguf | default |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, e in sorted(runs.items(), key=lambda kv: kv[1].get("finished") or kv[1].get("updated") or ""):
        if k.startswith("_"):
            continue
        ds = e.get("dataset") or {}
        ev = e.get("eval_loss_per_epoch") or {}
        evs = ", ".join(f"ep{a}={b}" for a, b in ev.items())
        if e.get("base_eval_loss") is not None:
            evs = f"base={e['base_eval_loss']}; " + evs
        gg = "; ".join(f"{q}: {Path(v['path']).name} ({v.get('size_gb')} GB)" for q, v in (e.get("gguf") or {}).items()) or "-"
        L.append(f"| {k} | {e.get('model_id') or '-'} | {e.get('status', '-')} | {Path(str(e.get('base_model') or '-')).name} | "
                 f"{ds.get('name') or '-'} ({ds.get('train_rows')}/{ds.get('eval_rows')}) | {e.get('steps') or '-'} | {evs or '-'} | "
                 f"{e.get('best_eval_loss') or '-'} | {_sc(e)} | {gg} | {'yes' if e.get('default') else 'no'} |")
    for k, e in sorted(runs.items()):
        if not k.startswith("_") and (e.get("dataset") or {}).get("source_mix"):
            mix = ", ".join(f"{a} {b}" for a, b in e["dataset"]["source_mix"].items())
            L.append(f"\n- **{k}** source mix: {mix}; adapter `{e.get('adapter')}`; finished {e.get('finished')}"
                     + (f"; note: {e['note']}" if e.get("note") else ""))
        elif not k.startswith("_") and e.get("note"):
            L.append(f"\n- **{k}**: {e['note']}")
    if "_self_data" in runs:
        s = runs["_self_data"]
        L += ["", f"Self-data loop: last improve {s.get('last_improve')}, verified rows added (recent) {s.get('selfplay_rows_added_recent')}, "
                  f"weak tools {', '.join(s.get('weak_tools') or []) or '-'}"]
    L += ["", f"## {TITLES['baselines']}", "", "| id | path | size | spotcheck | note |", "|---|---|---|---|---|"]
    for k, e in sorted(d["baselines"].items()):
        L.append(f"| {k} | `{e.get('path', '-')}` | {e.get('size_gb', '-')} GB | {_sc(e)} | {e.get('note', '')} |")
    L += ["", f"## {TITLES['archived']}", ""]
    for k, e in sorted(d["archived"].items()):
        L.append(f"- **{k}** (status={e.get('status', 'archived-experiment')}): {e.get('note', '')} `{e.get('path', '')}`")
    L += ["", f"## {TITLES['bases']}", "", "| model | path | format | state |", "|---|---|---|---|"]
    for k, e in sorted(d["bases"].items()):
        L.append(f"| {k} | `{e.get('path')}` | {e.get('format', 'hf safetensors')} | {e.get('state', '')} |")
    L += ["", "## Next", ""] + [f"{i}. {t}" for i, t in enumerate(d["next"], 1)]
    L += ["", "## History (latest 25)", ""]
    for h in d["history"][-25:][::-1]:
        L.append(f"- {h['ts']} {h['event']} {h['section']}/{h['id']}")
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------------------- seed
SEED_BASELINES = {
    "qwen2.5-1.5b-expand-b2-20260927": "expand-b2 (Sep 27)",
    "qwen2.5-1.5b-expand-ports-b3-20260927": "expand-ports-b3 (Sep 27)",
    "qwen2.5-1.5b-hive-expand-29-20260927": "hive-expand-29 (Sep 27)",
    "qwen2.5-1.5b-hive-expand-32-20260927": "hive-expand-32 (Sep 27)",
}
SEED_ARCHIVED = {
    "agent_lora_runs": ("108 per-agent LoRA r16 adapters on Qwen2.5-1.5B (tiny runs, near-init lora_B); byte-identical copies in D:\\ARCHIVE", "C:/models/checkpoints_lora/agent_lora_runs"),
    "dml-provider-expand-b2-20260927": ("DirectML provider-expand b2 adapter (source of expand-b2 GGUF)", "C:/models/checkpoints_lora/qwen2.5-1.5b-lora-realai-dml-provider-expand-b2-20260927"),
    "realai2-qwen2.5-1.5b-lora": ("early r16 / r8 LoRAs + 4-step smoke test (loss 0.488->0.454)", "D:/ARCHIVE/git-cleanup-2026-09/RealAI-C-backups/grok-worktrees-tsmit-realai/realai2/checkpoints_lora"),
    "safetensors-adapters-dump": ("~110 unlabeled 17 MB adapter_model_*.safetensors (no configs)", "D:/ARCHIVE/git-cleanup-2026-09/checkpoints_lora-dupes/20260925/safetensors-adapters"),
    "realai-1.0-instruct-gguf": ("old 'realai-1.0-instruct' Q4_K_M GGUFs (two different archs under one name)", "D:/ARCHIVE/git-cleanup-2026-09/models-dupes/20260927-074836/checkpoints_lora/_costume"),
    "truncated-ggufs": ("coder-7b __from-extracted_realai_core (1.6/5.4 GB) and 5x ~2 MB *_og_mess stubs: TRUNCATED, unusable", "D:/ARCHIVE/git-cleanup-2026-09"),
}
SEED_BASES = {
    "Qwen2.5-1.5B-Instruct": ("C:/models/hf/Qwen2.5-1.5B-Instruct", "complete (training base)"),
    "Qwen2.5-0.5B-Instruct": ("D:/hf_cache/models--Qwen--Qwen2.5-0.5B-Instruct", "complete"),
    "Qwen2.5-1.5B-Instruct (hf_cache)": ("D:/hf_cache/models--Qwen--Qwen2.5-1.5B-Instruct", "complete"),
    "Qwen2.5-Coder-1.5B-Instruct": ("D:/hf_cache/models--Qwen--Qwen2.5-Coder-1.5B-Instruct", "complete"),
    "Llama-3.2-1B-Instruct": ("D:/hf_cache/models--meta-llama--Llama-3.2-1B-Instruct", "complete"),
    "Qwen2.5-3B-Instruct": ("D:/hf_cache/models--Qwen--Qwen2.5-3B-Instruct", "complete (2/2 shards)"),
    "Qwen2.5-Coder-7B-Instruct": ("D:/hf_cache/models--Qwen--Qwen2.5-Coder-7B-Instruct", "complete (4/4 shards)"),
    "Qwen3-30B-A3B": ("D:/ARCHIVE/git-cleanup-2026-09/models-dupes/20260927-073922/checkpoints_lora/Qwen3-30B-A3B", "complete (16/16 shards, 61 GB)"),
}
SEED_NEXT = ["Spot-check realai-hive-1.5b (tools + no-tools) on :8081; register non-default unless >= 80%",
             "Restart 14B on :8080; run self_data generate (300-800 rows) -> improve -> rebuild realai-hive-sft",
             "Train Qwen2.5-3B-Instruct on the rebuilt hive dataset (base D:/hf_cache 3B)"]


def seed(gguf_dir: Optional[Path] = None) -> Dict[str, Any]:
    d = load()
    gdir = Path(gguf_dir) if gguf_dir else models_root() / "checkpoints_lora" / "gguf"
    for k, note in SEED_BASELINES.items():
        p = gdir / f"{k}-Q5_K_M.gguf"
        update("baselines", k, "seed", {"path": str(p), "quant": "Q5_K_M", "base_model": "Qwen2.5-1.5B-Instruct", "note": note,
                                        "size_gb": round(p.stat().st_size / 1e9, 3) if p.is_file() else None,
                                        "status": "exported-baseline"}, d)
    for k, (note, path) in SEED_ARCHIVED.items():
        update("archived", k, "seed", {"note": note, "path": path, "status": "archived-experiment"}, d)
    for k, (path, state) in SEED_BASES.items():
        update("bases", k, "seed", {"path": path, "state": state}, d)
    if not d["next"]:
        set_next(SEED_NEXT, d)
    save(d)
    return d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m realai.training.ledger")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seed"); s.add_argument("--gguf-dir")
    b = sub.add_parser("backfill-run", help="record an existing run dir (train_result/eval_report/gguf)")
    b.add_argument("run_dir"); b.add_argument("--model-id"); b.add_argument("--quant", default="Q5_K_M"); b.add_argument("--note")
    b.add_argument("--base-eval-loss", type=float)
    sc = sub.add_parser("spotcheck", help="record an existing spotcheck report"); sc.add_argument("report"); sc.add_argument("--model-id", required=True)
    n = sub.add_parser("next"); n.add_argument("items", nargs="+")
    sub.add_parser("render"); sub.add_parser("path")
    a = ap.parse_args(argv)
    if a.cmd == "seed":
        seed(a.gguf_dir)
    elif a.cmd == "backfill-run":
        out = Path(a.run_dir)
        res = json.loads((out / "train_result.json").read_text(encoding="utf-8"))
        on_train(out, res, model_id=a.model_id)
        ev = out / "eval_report.json"
        if ev.is_file():
            on_eval(out, json.loads(ev.read_text(encoding="utf-8")))
        elif a.base_eval_loss is not None:
            update("runs", run_id(out), "eval", {"base_eval_loss": a.base_eval_loss})
        if a.note:
            update("runs", run_id(out), "note", {"note": a.note})
        if a.model_id:
            for g in sorted((out / "gguf").glob(f"{a.model_id}-{a.quant}.gguf")) if (out / "gguf").is_dir() else []:
                on_export(out, g, a.quant, a.model_id)
    elif a.cmd == "spotcheck":
        on_spotcheck(json.loads(Path(a.report).read_text(encoding="utf-8")), Path(a.report), a.model_id)
    elif a.cmd == "next":
        set_next(a.items)
    elif a.cmd == "render":
        save(load())
    print(md_path())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
