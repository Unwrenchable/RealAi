#!/usr/bin/env python3
"""Promote dest_empty_promotable from gold shelf into live RealAI-clean, then unlink archive junctions.

NO deletes of D: archive data. NO RealAI runtime. Never overwrite non-empty live files.
Never Remove-Item -Recurse / rd /s on junctions.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

MANIFEST = Path(r"C:\RealAI-clean\docs\recovery\2026-09-13-final-gold\dest_empty_promotable.jsonl")
GOLD_ROOT = Path(r"C:\RealAI-gold")
LIVE_ROOT = Path(r"C:\RealAI-clean")
REPORT_DIR = Path(r"C:\RealAI-clean\docs\recovery\2026-09-13-final-gold")
LOG_PATH = REPORT_DIR / "promote_log.jsonl"
REPORT_PATH = REPORT_DIR / "PROMOTE_REPORT.md"

JUNCTION_NAMES = ("_quarantine", "imports", "recovered")
BLOCKED_TOP = {n.lower() for n in JUNCTION_NAMES}
ARCHIVE_ROOT = Path(r"D:\RealAI-archive")

README_TEMPLATE = (
    "This directory is a local placeholder.\n"
    "\n"
    "The historical archive for this path lives at:\n"
    "  {archive_path}\n"
    "\n"
    "The gold shelf lives at:\n"
    "  C:\\RealAI-gold\\\n"
    "\n"
    "The previous junction from C:\\RealAI-clean\\{name} -> {archive_path}\n"
    "was unlinked on purpose. D: archive data was NOT deleted.\n"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def pt_now() -> str:
    # America/Los_Angeles is UTC-7 on 2026-09-13 (PDT)
    from datetime import timedelta
    pt = datetime.now(timezone.utc) - timedelta(hours=7)
    return pt.strftime("%Y-%m-%d %H:%M:%S PT")


def is_unsafe_rel(rel: str, root: Path) -> str | None:
    if rel is None:
        return "empty_rel"
    rel_s = str(rel).strip()
    if not rel_s:
        return "empty_rel"
    # Normalize separators for inspection only
    inspect = rel_s.replace("/", "\\")
    if os.path.isabs(inspect):
        return "absolute_path"
    if len(inspect) >= 2 and inspect[1] == ":":
        return "absolute_path"
    if inspect.startswith("\\\\") or inspect.startswith("\\"):
        return "absolute_path"
    parts = [p for p in inspect.split("\\") if p]
    if not parts:
        return "empty_rel"
    if any(p == ".." for p in parts):
        return "dotdot"
    if parts[0].lower() in BLOCKED_TOP:
        return "junction_target"
    # Resolve against root and ensure still inside
    try:
        candidate = (root.joinpath(*parts)).resolve()
        candidate.relative_to(root.resolve())
    except Exception:
        return "outside_root"
    return None


def log_row(fh, obj: dict) -> None:
    fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def dir_file_count(path: Path, limit_walk: bool = True) -> tuple[int, int]:
    """Return (file_count, byte_count) with a shallow+bounded walk for verification."""
    files = 0
    nbytes = 0
    if not path.exists():
        return 0, 0
    try:
        for dirpath, dirnames, filenames in os.walk(path, followlinks=False):
            # do not follow junctions/symlinks
            for fn in filenames:
                fp = os.path.join(dirpath, fn)
                files += 1
                try:
                    nbytes += os.path.getsize(fp)
                except OSError:
                    pass
            if files > 50 and limit_walk:
                # enough to prove populated; still walk fully if not limited
                pass
            if not limit_walk:
                continue
            # For verification we still want a decent sample; walk fully but this can be huge.
            # Caller can set limit_walk False for full, True we'll still walk fully for archive
            # confirmation of existence+populated using a max of 500 files.
            if files >= 500:
                break
    except OSError:
        pass
    return files, nbytes


def promote() -> tuple[Counter, int]:
    stats: Counter = Counter()
    promoted_bytes = 0
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    with open(MANIFEST, "r", encoding="utf-8") as mf, open(LOG_PATH, "w", encoding="utf-8") as log:
        for lineno, line in enumerate(mf, 1):
            raw = line.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as e:
                log_row(log, {"status": "skipped", "reason": "bad_json", "lineno": lineno, "error": str(e)})
                stats["skipped_bad_json"] += 1
                continue

            rel = row.get("inferred_live_rel") or ""
            gold_rel = row.get("gold_rel") or rel
            expected_hash = row.get("hash")
            expected_size = row.get("size")
            src = row.get("src")

            reason = is_unsafe_rel(rel, LIVE_ROOT)
            if reason:
                log_row(log, {
                    "status": "blocked",
                    "reason": reason,
                    "inferred_live_rel": rel,
                    "gold_rel": gold_rel,
                    "lineno": lineno,
                })
                stats["blocked"] += 1
                stats[f"blocked_{reason}"] += 1
                continue

            gold_reason = is_unsafe_rel(gold_rel, GOLD_ROOT)
            if gold_reason:
                log_row(log, {
                    "status": "blocked",
                    "reason": f"gold_{gold_reason}",
                    "inferred_live_rel": rel,
                    "gold_rel": gold_rel,
                    "lineno": lineno,
                })
                stats["blocked"] += 1
                stats[f"blocked_gold_{gold_reason}"] += 1
                continue

            rel_parts = [p for p in str(rel).replace("/", "\\").split("\\") if p]
            gold_parts = [p for p in str(gold_rel).replace("/", "\\").split("\\") if p]

            gold_path = GOLD_ROOT.joinpath(*gold_parts)
            if not gold_path.is_file():
                fallback = LIVE_ROOT  # placeholder
                gold_path_fb = GOLD_ROOT.joinpath(*rel_parts)
                if gold_path_fb.is_file():
                    gold_path = gold_path_fb
                else:
                    log_row(log, {
                        "status": "missing_gold",
                        "reason": "gold_file_missing",
                        "inferred_live_rel": rel,
                        "gold_rel": gold_rel,
                        "gold_path": str(gold_path),
                        "lineno": lineno,
                    })
                    stats["missing_gold"] += 1
                    continue

            live_path = LIVE_ROOT.joinpath(*rel_parts)

            try:
                live_resolved = live_path.resolve()
                live_resolved.relative_to(LIVE_ROOT.resolve())
            except Exception:
                log_row(log, {
                    "status": "blocked",
                    "reason": "outside_live_root",
                    "inferred_live_rel": rel,
                    "live_path": str(live_path),
                    "lineno": lineno,
                })
                stats["blocked"] += 1
                stats["blocked_outside_live_root"] += 1
                continue

            if live_path.exists():
                if live_path.is_file() and live_path.stat().st_size == 0:
                    pass  # allowed
                elif live_path.is_file() and live_path.stat().st_size > 0:
                    log_row(log, {
                        "status": "skipped",
                        "reason": "live_nonempty",
                        "inferred_live_rel": rel,
                        "live_path": str(live_path),
                        "live_size": live_path.stat().st_size,
                        "lineno": lineno,
                    })
                    stats["skipped_live_nonempty"] += 1
                    continue
                else:
                    log_row(log, {
                        "status": "skipped",
                        "reason": "live_exists_not_empty_file",
                        "inferred_live_rel": rel,
                        "live_path": str(live_path),
                        "lineno": lineno,
                    })
                    stats["skipped_live_exists_not_empty_file"] += 1
                    continue

            try:
                live_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(gold_path, live_path)
                copied_size = live_path.stat().st_size
                log_row(log, {
                    "status": "promoted",
                    "inferred_live_rel": rel,
                    "gold_rel": gold_rel,
                    "gold_path": str(gold_path),
                    "live_path": str(live_path),
                    "size": copied_size,
                    "expected_size": expected_size,
                    "hash": expected_hash,
                    "src": src,
                    "lineno": lineno,
                })
                stats["promoted"] += 1
                promoted_bytes += copied_size
                if expected_size is not None and copied_size != expected_size:
                    stats["size_mismatch_after_copy"] += 1
            except Exception as e:
                log_row(log, {
                    "status": "skipped",
                    "reason": "copy_error",
                    "error": str(e),
                    "inferred_live_rel": rel,
                    "gold_path": str(gold_path),
                    "live_path": str(live_path),
                    "lineno": lineno,
                })
                stats["skipped_copy_error"] += 1

    return stats, promoted_bytes


def cmd_dir_al(path: str) -> str:
    r = subprocess.run(["cmd", "/c", "dir", "/AL", path], capture_output=True, text=True)
    return (r.stdout or "") + (r.stderr or "")


def fsutil_query(path: str) -> str:
    r = subprocess.run(["fsutil", "reparsepoint", "query", path], capture_output=True, text=True)
    return (r.stdout or "") + (r.stderr or "")


def is_reparse_point(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        if hasattr(os.path, "isjunction") and os.path.isjunction(path):
            return True
    except OSError:
        pass
    try:
        st = os.lstat(path)
        attrs = getattr(st, "st_file_attributes", 0)
        return bool(attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except OSError:
        return False


def archive_snapshot() -> dict:
    snap = {}
    for name in JUNCTION_NAMES:
        p = ARCHIVE_ROOT / name
        exists = p.exists()
        files, nbytes = (0, 0)
        n_entries = 0
        if exists:
            try:
                n_entries = sum(1 for _ in os.scandir(p))
            except OSError:
                n_entries = -1
            files, nbytes = dir_file_count(p, limit_walk=True)
        snap[name] = {
            "path": str(p),
            "exists": exists,
            "top_entries": n_entries,
            "sampled_files": files,
            "sampled_bytes": nbytes,
        }
    return snap


def unlink_junctions() -> list[dict]:
    results = []
    for name in JUNCTION_NAMES:
        link = LIVE_ROOT / name
        target = ARCHIVE_ROOT / name
        rec = {
            "name": name,
            "link": str(link),
            "expected_target": str(target),
            "before_is_reparse": False,
            "before_fsutil": "",
            "removed": False,
            "placeholder_created": False,
            "error": None,
            "after_is_reparse": None,
            "after_is_dir": None,
        }
        rec["before_fsutil"] = fsutil_query(str(link))
        rec["before_is_reparse"] = is_reparse_point(link)
        rec["before_dir_al"] = cmd_dir_al(str(LIVE_ROOT))

        if not rec["before_is_reparse"]:
            rec["error"] = "not_a_junction_skip_remove"
            results.append(rec)
            continue

        # Confirm target still exists BEFORE unlink
        rec["target_exists_before"] = target.exists()

        # rmdir on the junction removes the link only. NEVER rd /s, NEVER Remove-Item -Recurse.
        r = subprocess.run(["cmd", "/c", "rmdir", str(link)], capture_output=True, text=True)
        rec["rmdir_returncode"] = r.returncode
        rec["rmdir_stdout"] = (r.stdout or "").strip()
        rec["rmdir_stderr"] = (r.stderr or "").strip()
        if r.returncode != 0:
            rec["error"] = f"rmdir_failed:{r.returncode}:{rec['rmdir_stderr']}"
            results.append(rec)
            continue
        rec["removed"] = True

        # Create empty placeholder dir + README
        try:
            link.mkdir(parents=False, exist_ok=False)
            readme = link / "README.txt"
            readme.write_text(
                README_TEMPLATE.format(archive_path=str(target), name=name),
                encoding="utf-8",
            )
            rec["placeholder_created"] = True
        except Exception as e:
            rec["error"] = f"placeholder_failed:{e}"

        rec["after_is_reparse"] = is_reparse_point(link)
        rec["after_is_dir"] = link.is_dir() and not is_reparse_point(link)
        rec["target_exists_after"] = target.exists()
        rec["after_fsutil"] = fsutil_query(str(link))
        results.append(rec)
    return results


def write_report(stats: Counter, promoted_bytes: int, archive_before: dict, archive_after: dict, junctions: list[dict]) -> None:
    skipped_reasons = {k: v for k, v in sorted(stats.items()) if k.startswith("skipped_")}
    blocked_reasons = {k: v for k, v in sorted(stats.items()) if k.startswith("blocked_")}
    lines = []
    lines.append("# Promote dest_empty_promotable + unlink archive junctions")
    lines.append("")
    lines.append(f"- Generated: {pt_now()} ({utc_now()})")
    lines.append(f"- Manifest: `{MANIFEST}`")
    lines.append(f"- Gold shelf: `{GOLD_ROOT}`")
    lines.append(f"- Live root: `{LIVE_ROOT}`")
    lines.append(f"- Log: `{LOG_PATH}`")
    lines.append("")
    lines.append("## Promote results")
    lines.append("")
    lines.append(f"- **promoted:** {stats.get('promoted', 0)} files, **{promoted_bytes}** bytes")
    lines.append(f"- **missing_gold:** {stats.get('missing_gold', 0)}")
    lines.append(f"- **blocked (total):** {stats.get('blocked', 0)}")
    lines.append(f"- **size_mismatch_after_copy:** {stats.get('size_mismatch_after_copy', 0)}")
    lines.append("")
    lines.append("### Skipped by reason")
    lines.append("")
    if skipped_reasons:
        for k, v in skipped_reasons.items():
            lines.append(f"- `{k}`: {v}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("### Blocked by reason")
    lines.append("")
    if blocked_reasons:
        for k, v in blocked_reasons.items():
            lines.append(f"- `{k}`: {v}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("Rules applied: copy only when gold file exists and live path is missing or size 0;")
    lines.append("never overwrite non-empty live files; skip unsafe rels (absolute, `..`, outside live root,")
    lines.append("or into `_quarantine` / `imports` / `recovered` junction targets). Parent dirs created as needed.")
    lines.append("")
    lines.append("## Junction unlink")
    lines.append("")
    lines.append("Method: `cmd /c rmdir <junction>` (removes the link only). Never `rd /s`, never `Remove-Item -Recurse`.")
    lines.append("Placeholders: empty directories with `README.txt` pointing at `D:\\RealAI-archive\\...` and `C:\\RealAI-gold\\`.")
    lines.append("")
    for rec in junctions:
        lines.append(f"### `{rec['name']}`")
        lines.append("")
        lines.append(f"- link: `{rec['link']}`")
        lines.append(f"- expected target: `{rec['expected_target']}`")
        lines.append(f"- was reparse/junction before: {rec.get('before_is_reparse')}")
        lines.append(f"- rmdir returncode: {rec.get('rmdir_returncode')}")
        lines.append(f"- removed: {rec.get('removed')}")
        lines.append(f"- placeholder created: {rec.get('placeholder_created')}")
        lines.append(f"- after is ordinary dir (not reparse): {rec.get('after_is_dir')}")
        lines.append(f"- after is reparse: {rec.get('after_is_reparse')}")
        lines.append(f"- target exists after: {rec.get('target_exists_after')}")
        if rec.get("error"):
            lines.append(f"- **error:** {rec['error']}")
        lines.append("")
    lines.append("## D: archive still present")
    lines.append("")
    lines.append("### Before unlink")
    lines.append("")
    for name, snap in archive_before.items():
        lines.append(
            f"- `{snap['path']}` exists={snap['exists']} top_entries={snap['top_entries']} "
            f"sampled_files={snap['sampled_files']} sampled_bytes={snap['sampled_bytes']}"
        )
    lines.append("")
    lines.append("### After unlink")
    lines.append("")
    for name, snap in archive_after.items():
        lines.append(
            f"- `{snap['path']}` exists={snap['exists']} top_entries={snap['top_entries']} "
            f"sampled_files={snap['sampled_files']} sampled_bytes={snap['sampled_bytes']}"
        )
    lines.append("")
    lines.append("## dir /AL C:\\RealAI-clean (after)")
    lines.append("")
    lines.append("```")
    lines.append(cmd_dir_al(str(LIVE_ROOT)).rstrip())
    lines.append("```")
    lines.append("")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    print(f"START promote {pt_now()}", flush=True)
    if not MANIFEST.is_file():
        print(f"FATAL missing manifest {MANIFEST}", file=sys.stderr)
        return 2
    archive_before = archive_snapshot()
    print("ARCHIVE BEFORE", json.dumps(archive_before), flush=True)
    stats, promoted_bytes = promote()
    print("PROMOTE DONE", dict(stats), "bytes", promoted_bytes, flush=True)
    print("UNLINK START", flush=True)
    junctions = unlink_junctions()
    archive_after = archive_snapshot()
    print("ARCHIVE AFTER", json.dumps(archive_after), flush=True)
    write_report(stats, promoted_bytes, archive_before, archive_after, junctions)
    print("REPORT", REPORT_PATH, flush=True)
    print("LOG", LOG_PATH, flush=True)
    # Summary JSON on stdout for parent
    summary = {
        "promoted": stats.get("promoted", 0),
        "promoted_bytes": promoted_bytes,
        "missing_gold": stats.get("missing_gold", 0),
        "blocked": stats.get("blocked", 0),
        "stats": dict(stats),
        "junctions": [
            {
                "name": j["name"],
                "removed": j.get("removed"),
                "placeholder_created": j.get("placeholder_created"),
                "after_is_dir": j.get("after_is_dir"),
                "after_is_reparse": j.get("after_is_reparse"),
                "target_exists_after": j.get("target_exists_after"),
                "error": j.get("error"),
            }
            for j in junctions
        ],
        "archive_after": archive_after,
        "report": str(REPORT_PATH),
        "log": str(LOG_PATH),
    }
    print("SUMMARY_JSON", json.dumps(summary), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
