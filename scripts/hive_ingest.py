#!/usr/bin/env python
"""Ingest raw hive records into staged ability_surface-shaped training candidates.

Reads  <inbox>/YYYY-MM-DD/<bot>.jsonl  (hive.v1 records), validates, rejects any record with
secrets (never rewrites), dedupes, and writes:
    training/data/_staging/hive_candidates_<date>.jsonl            rows: {"messages":[user, assistant]}
    training/data/_staging/hive_candidates_<date>.manifest.jsonl   provenance: id, content_hash, bot, category
    training/data/_staging/hive_rejects_<date>.json                reasons only, never content

It NEVER touches training/data/ability_surface.jsonl and NEVER writes training/data/hive_ops.jsonl;
promotion is a reviewed PR (see docs/HIVE.md). Hive rows are for v3, not v2.

Usage:
    python scripts/hive_ingest.py <inbox> [--date YYYY-MM-DD] [--dry-run]
    python scripts/hive_ingest.py <inbox> --prune-older-than-days 90          # lists only
    python scripts/hive_ingest.py <inbox> --prune-older-than-days 90 --apply  # deletes old raw inbox files
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from realai.hive_records.redact import scan_record  # noqa: E402
from realai.hive_records.schema import validate_record  # noqa: E402

DEFAULT_ALLOWLIST = ("chief", "qa-lead", "release-devops")
DATE_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}$")
UUID_RX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
MAX_LINE_BYTES = 64 * 1024


def slug(name: str) -> str:
    """'Release & DevOps' -> 'release-devops', 'QA Lead' -> 'qa-lead'."""
    return re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")


def content_hash(rec: Dict[str, Any]) -> str:
    """Hash of what the record says, ignoring id, ts and bot.id (so re-sent copies collapse)."""
    core = {
        "bot": slug(rec["bot"]["name"]),
        "product": rec["product"],
        "task": rec["task"],
        "actions": rec["actions"],
        "verification": rec["verification"],
        "outcome": rec["outcome"],
    }
    blob = json.dumps(core, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def to_ability_row(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Map a hive.v1 record to the exact ability_surface.jsonl row shape.

    ability_surface rows are ``{"messages": [{"role": "user", ...}, {"role": "assistant", ...}]}``
    and nothing else (no extra keys), so provenance lives in the manifest, not in the row.
    """
    t, v = rec["task"], rec["verification"]
    user = f"How did the bot team handle this {t['category']} task for {rec['product']}: {t['ask']}"
    steps = "; ".join(f"{a['step']}. [{a['tool_kind']}] {a['summary']}" for a in rec["actions"])
    parts = [f"Outcome: {rec['outcome']}.", f"Steps: {steps}."]
    ev = f" Evidence: {v['evidence']}" if v.get("evidence") else ""
    parts.append(f"Verified with `{v['command']}` -> {v['result']}.{ev}")
    if rec.get("blockers"):
        parts.append("Blockers: " + "; ".join(rec["blockers"]) + ".")
    if rec.get("links"):
        parts.append("Links: " + ", ".join(rec["links"]) + ".")
    if rec.get("approval"):
        parts.append(f"Approval: {rec['approval']}.")
    return {"messages": [{"role": "user", "content": user},
                         {"role": "assistant", "content": " ".join(parts)}]}


def _date_dirs(inbox: Path, only: Optional[str]) -> List[Path]:
    if not inbox.is_dir():
        return []
    dirs = sorted(d for d in inbox.iterdir() if d.is_dir() and DATE_DIR.match(d.name))
    return [d for d in dirs if only is None or d.name == only]


def _load_seen(out_dir: Path) -> Tuple[set, set]:
    ids, hashes = set(), set()
    if out_dir.is_dir():
        for mf in out_dir.glob("hive_candidates_*.manifest.jsonl"):
            for line in mf.read_text(encoding="utf-8").splitlines():
                try:
                    m = json.loads(line)
                except ValueError:
                    continue
                ids.add(m.get("id"))
                hashes.add(m.get("content_hash"))
    return ids, hashes


def ingest(inbox: Path, out_dir: Path, allowlist: Iterable[str] = DEFAULT_ALLOWLIST,
           only_date: Optional[str] = None, run_date: Optional[str] = None,
           dry_run: bool = False) -> Dict[str, Any]:
    allow = {slug(a) for a in allowlist}
    run_date = run_date or date.today().isoformat()
    seen_ids, seen_hashes = _load_seen(out_dir)
    rows: List[Dict[str, Any]] = []
    manifest: List[Dict[str, Any]] = []
    rejects: List[Dict[str, Any]] = []
    stats = {"files": 0, "records": 0, "kept": 0, "rejected": 0, "duplicates": 0, "skipped_files": 0}

    for d in _date_dirs(inbox, only_date):
        for f in sorted(d.glob("*.jsonl")):
            rel = f"{d.name}/{f.name}"
            stats["files"] += 1
            if slug(f.stem) not in allow:
                stats["skipped_files"] += 1
                rejects.append({"file": rel, "line": None, "id": None, "reasons": ["bot_not_allowlisted"]})
                continue
            for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if not line.strip():
                    continue
                stats["records"] += 1

                def reject(reasons: List[str], rid: Optional[str] = None) -> None:
                    stats["rejected"] += 1
                    safe_id = rid if isinstance(rid, str) and UUID_RX.match(rid) else None
                    rejects.append({"file": rel, "line": n, "id": safe_id, "reasons": sorted(set(reasons))})

                if len(line.encode("utf-8")) > MAX_LINE_BYTES:
                    reject(["line:too_long"])
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    reject(["json:invalid"])
                    continue
                rid = rec.get("id") if isinstance(rec, dict) else None
                errs = validate_record(rec)
                if errs:
                    reject(errs, rid)
                    continue
                if slug(rec["bot"]["name"]) != slug(f.stem):
                    reject(["bot:file_mismatch"], rid)
                    continue
                hits = scan_record(rec)
                if hits:
                    reject([f"secret:{h}" for h in hits], rid)
                    continue
                ch = content_hash(rec)
                if rec["id"] in seen_ids or ch in seen_hashes:
                    stats["duplicates"] += 1
                    continue
                row = to_ability_row(rec)
                row_hits = scan_record(row)  # defence in depth on the mapped text
                if row_hits:
                    reject([f"secret:{h}" for h in row_hits], rid)
                    continue
                seen_ids.add(rec["id"])
                seen_hashes.add(ch)
                rows.append(row)
                manifest.append({"id": rec["id"], "content_hash": ch, "bot": slug(rec["bot"]["name"]),
                                 "category": rec["task"]["category"], "source": rel, "line": n})
                stats["kept"] += 1

    result: Dict[str, Any] = {"stats": stats, "rows": rows, "manifest": manifest, "rejects": rejects,
                              "dry_run": dry_run, "written": []}
    if dry_run:
        return result
    out_dir.mkdir(parents=True, exist_ok=True)
    if rows:
        cand = out_dir / f"hive_candidates_{run_date}.jsonl"
        man = out_dir / f"hive_candidates_{run_date}.manifest.jsonl"
        with cand.open("a", encoding="utf-8", newline="\n") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        with man.open("a", encoding="utf-8", newline="\n") as fh:
            for m in manifest:
                fh.write(json.dumps(m, ensure_ascii=False) + "\n")
        result["written"] += [str(cand), str(man)]
    rep = out_dir / f"hive_rejects_{run_date}.json"
    rep.write_text(json.dumps({"run_date": run_date, "stats": stats, "rejects": rejects}, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    result["written"].append(str(rep))
    return result


def prune(inbox: Path, days: int, apply: bool = False, today: Optional[date] = None) -> List[Path]:
    """List (and only with apply=True delete) raw inbox *.jsonl files in date folders older than N days."""
    cutoff = (today or date.today()) - timedelta(days=days)
    old: List[Path] = []
    for d in _date_dirs(inbox, None):
        try:
            when = datetime.strptime(d.name, "%Y-%m-%d").date()
        except ValueError:
            continue
        if when < cutoff:
            old.extend(sorted(d.glob("*.jsonl")))
    if apply:
        for f in old:
            f.unlink()
        for d in _date_dirs(inbox, None):
            if not any(d.iterdir()):
                d.rmdir()
    return old


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Ingest hive.v1 records into staged training candidates.")
    p.add_argument("inbox", help="inbox root containing YYYY-MM-DD/<bot>.jsonl")
    p.add_argument("--out-dir", default=str(REPO_ROOT / "training" / "data" / "_staging"))
    p.add_argument("--date", help="only ingest this YYYY-MM-DD inbox folder")
    p.add_argument("--allow-bot", action="append", help="override allowlist (repeatable); default: Chief, QA Lead, Release & DevOps")
    p.add_argument("--dry-run", action="store_true", help="validate and report counts; write nothing")
    p.add_argument("--prune-older-than-days", type=int, metavar="N", help="list raw inbox files older than N days")
    p.add_argument("--apply", action="store_true", help="with --prune-older-than-days: actually delete")
    a = p.parse_args(argv)
    inbox = Path(a.inbox)

    if a.prune_older_than_days is not None:
        old = prune(inbox, a.prune_older_than_days, apply=a.apply and not a.dry_run)
        verb = "deleted" if (a.apply and not a.dry_run) else "would delete (list only; pass --apply)"
        for f in old:
            print(f"{verb}: {f}")
        print(f"{len(old)} file(s) older than {a.prune_older_than_days} days")
        return 0
    if a.apply:
        p.error("--apply only valid with --prune-older-than-days")

    res = ingest(inbox, Path(a.out_dir), a.allow_bot or DEFAULT_ALLOWLIST, a.date, a.date, a.dry_run)
    s = res["stats"]
    print(f"files={s['files']} skipped_files={s['skipped_files']} records={s['records']} kept={s['kept']} "
          f"rejected={s['rejected']} duplicates={s['duplicates']}" + (" [dry-run: nothing written]" if a.dry_run else ""))
    for w in res["written"]:
        print("wrote", w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
