# -*- coding: utf-8 -*-
"""Final gold archaeology: unique-hash survivors from D: archives vs live C:\\RealAI-clean."""
from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

OUT = Path(r"C:\RealAI-clean\docs\recovery\2026-09-13-final-gold")
GOLD = Path(r"C:\RealAI-gold")
LIVE_ROOT = Path(r"C:\RealAI-clean")

LIVE_SUBS = ["realai", "apps", "frontend", "scripts", "providers", "packages", "agents", "abilities"]
ARCHIVE_ROOTS = [
    Path(r"D:\RealAI-archive\_quarantine"),
    Path(r"D:\RealAI-archive\imports"),
    Path(r"D:\RealAI-archive\recovered"),
]
SHALLOW_ROOT = Path(r"D:\realai_archives")

INTERESTING = {
    ".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".json", ".toml", ".yaml", ".yml",
    ".md", ".ps1", ".bat", ".cmd", ".html", ".css",
}
WEIGHT = {".gguf", ".bin", ".safetensors", ".pt", ".pth", ".onnx", ".ckpt"}
SKIP_DIR_NAMES = {
    "node_modules", "__pycache__", ".git", ".venv", "venv", "env",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".next", "coverage", "wheels",
}
NEST_PATTERNS = [
    re.compile(r"RealAI_Recovery", re.I),
    re.compile(r"C__realai", re.I),
    re.compile(r"grok_export", re.I),
    re.compile(r"grok-export", re.I),
]

CAP_BYTES = 8 * 1024 ** 3  # 8GB
LOG_EVERY = 200
PRIORITY_EXT = {".py": 0, ".ts": 1, ".tsx": 2, ".js": 3, ".mjs": 4, ".cjs": 5}

log_path = OUT / "scan_log.txt"
skipped_heavy = defaultdict(int)
errors = []

def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def sha256_file(path: Path, bufsize: int = 1024 * 1024) -> str | None:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(bufsize)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except OSError as e:
        errors.append(f"{path}: {e}")
        return None

def should_skip_dir(name: str) -> bool:
    if name in SKIP_DIR_NAMES:
        return True
    if name.startswith(".") and name not in {".github", ".vscode", ".cursor"}:
        # still allow walking into some; but skip common junk
        if name in {".git", ".venv", ".tox", ".mypy_cache", ".pytest_cache", ".next"}:
            return True
    return False

def is_nest_path(parts: tuple) -> bool:
    joined = "\\".join(parts)
    for pat in NEST_PATTERNS:
        if pat.search(joined):
            return True
    return False

def path_score(rel: str) -> tuple:
    """Lower is better (prefer canonical)."""
    low = rel.lower().replace("/", "\\")
    score = 0
    if "realai\\modules" in low:
        score -= 1000
    elif "\\realai\\" in "\\" + low + "\\" or low.startswith("realai\\"):
        score -= 500
    if "apps\\vscode" in low:
        score -= 400
    if "\\apps\\" in "\\" + low:
        score -= 200
    # deep nests penalize
    depth = low.count("\\")
    score += depth * 10
    if is_nest_path(tuple(low.split("\\"))):
        score += 5000
    # shorter path preferred
    score += len(low) // 20
    return (score, len(low), low)

def infer_live_dest(src: Path, archive_root: Path) -> str | None:
    """Infer a sensible live-relative dest under realai/ or apps/ (or scripts/frontend etc)."""
    try:
        rel = src.relative_to(archive_root)
    except ValueError:
        rel = Path(src.name)
    parts = list(rel.parts)
    # find anchors
    anchors = ("realai", "apps", "frontend", "scripts", "providers", "packages", "agents", "abilities")
    low_parts = [p.lower() for p in parts]
    for i, p in enumerate(low_parts):
        if p in anchors:
            # use original casing from parts from i onward
            return str(Path(*parts[i:]))
    # try modules/... -> realai/modules/...
    for i, p in enumerate(low_parts):
        if p == "modules" and i + 1 < len(parts):
            return str(Path("realai") / Path(*parts[i:]))
    return None

def dest_empty_or_missing(live_rel: str) -> bool:
    dest = LIVE_ROOT / live_rel
    if not dest.exists():
        return True
    try:
        if dest.is_file() and dest.stat().st_size == 0:
            return True
    except OSError:
        return False
    return False

def walk_interesting(root: Path, shallow_max_depth: int | None = None):
    """Yield Path for interesting files; skip heavy dirs."""
    root = Path(root)
    if not root.exists():
        log(f"MISSING root: {root}")
        return
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, onerror=lambda e: errors.append(str(e))):
        # prune dirs
        pruned = []
        for d in list(dirnames):
            if should_skip_dir(d):
                skipped_heavy[f"dir:{d}"] += 1
                dirnames.remove(d)
                continue
            # skip nested snapshot trees as wholesale dirs? still walk for unique files per rules
            # but skip venvs by pattern
            if d.endswith("_venv") or d.endswith("-venv"):
                skipped_heavy["dir:venv_pattern"] += 1
                dirnames.remove(d)
                continue
        rel_depth = len(Path(dirpath).relative_to(root).parts) if Path(dirpath) != root else 0
        if shallow_max_depth is not None and rel_depth >= shallow_max_depth:
            dirnames[:] = []
        for fn in filenames:
            ext = Path(fn).suffix.lower()
            if ext in WEIGHT:
                skipped_heavy[f"weight:{ext}"] += 1
                continue
            if ext not in INTERESTING:
                skipped_heavy[f"skip_ext:{ext or '(none)'}"] += 1
                continue
            # skip huge non-priority files > 50MB
            fp = Path(dirpath) / fn
            try:
                sz = fp.stat().st_size
            except OSError as e:
                errors.append(f"{fp}: {e}")
                continue
            if sz > 50 * 1024 * 1024 and ext not in {".py", ".ts", ".tsx", ".js", ".json", ".md"}:
                skipped_heavy["too_large"] += 1
                continue
            yield fp, sz

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    GOLD.mkdir(parents=True, exist_ok=True)
    # reset log
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"Gold archaeology start {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    # --- Phase 1: LIVE hash index ---
    log("PHASE1: building live hash index")
    live_hashes: dict[str, dict] = {}  # hash -> {relpath, size}
    live_count = 0
    live_hash_path = OUT / "live_hashes.jsonl"
    with open(live_hash_path, "w", encoding="utf-8") as outf:
        for sub in LIVE_SUBS:
            root = LIVE_ROOT / sub
            if not root.exists():
                log(f"  live missing: {root}")
                continue
            log(f"  indexing {root}")
            for fp, sz in walk_interesting(root):
                h = sha256_file(fp)
                if not h:
                    continue
                try:
                    rel = str(fp.relative_to(LIVE_ROOT)).replace("\\", "/")
                except ValueError:
                    rel = str(fp)
                rec = {"hash": h, "relpath": rel, "size": sz}
                outf.write(json.dumps(rec) + "\n")
                if h not in live_hashes:
                    live_hashes[h] = rec
                live_count += 1
                if live_count % LOG_EVERY == 0:
                    log(f"  live files hashed: {live_count}")
    log(f"PHASE1 done: {live_count} files, {len(live_hashes)} unique hashes")

    # --- Phase 2: archive walk ---
    log("PHASE2: walking archives")
    # hash -> best candidate info
    candidates: dict[str, dict] = {}
    scanned = 0
    dup_of_live = 0

    def consider(fp: Path, sz: int, archive_root: Path, shallow: bool = False):
        nonlocal scanned, dup_of_live
        scanned += 1
        if scanned % LOG_EVERY == 0:
            log(f"  archive scanned: {scanned} unique_cands={len(candidates)} dups={dup_of_live}")
        h = sha256_file(fp)
        if not h:
            return
        if h in live_hashes:
            dup_of_live += 1
            return
        try:
            rel_from_arch = str(fp.relative_to(archive_root)).replace("\\", "/")
        except ValueError:
            rel_from_arch = fp.name
        full = str(fp)
        score = path_score(rel_from_arch)
        entry = {
            "hash": h,
            "size": sz,
            "path": full,
            "archive_root": str(archive_root),
            "rel_from_arch": rel_from_arch,
            "ext": fp.suffix.lower(),
            "score": score[0],
            "shallow": shallow,
        }
        if h not in candidates or score < path_score(candidates[h]["rel_from_arch"]):
            candidates[h] = entry

    for ar in ARCHIVE_ROOTS:
        log(f"  deep walk: {ar}")
        for fp, sz in walk_interesting(ar):
            consider(fp, sz, ar, shallow=False)

    # shallow D:\realai_archives (depth 3)
    if SHALLOW_ROOT.exists():
        log(f"  shallow walk (depth<=3): {SHALLOW_ROOT}")
        for fp, sz in walk_interesting(SHALLOW_ROOT, shallow_max_depth=3):
            consider(fp, sz, SHALLOW_ROOT, shallow=True)
    else:
        log(f"  shallow root missing: {SHALLOW_ROOT}")

    log(f"PHASE2 done: scanned={scanned} unique_hashes={len(candidates)} dup_of_live={dup_of_live}")

    # --- Phase 3: classify ---
    log("PHASE3: classify")
    dest_empty = []
    orphans = []
    for h, c in candidates.items():
        live_rel = infer_live_dest(Path(c["path"]), Path(c["archive_root"]))
        c["inferred_live_rel"] = live_rel
        if live_rel and dest_empty_or_missing(live_rel):
            c["class"] = "dest_empty_unique"
            dest_empty.append(c)
        else:
            c["class"] = "unique_orphan"
            orphans.append(c)

    # write unique_candidates.jsonl
    cand_path = OUT / "unique_candidates.jsonl"
    with open(cand_path, "w", encoding="utf-8") as f:
        for h, c in sorted(candidates.items(), key=lambda x: x[1]["score"]):
            f.write(json.dumps({
                "hash": c["hash"],
                "size": c["size"],
                "path": c["path"],
                "rel_from_arch": c["rel_from_arch"],
                "ext": c["ext"],
                "class": c["class"],
                "inferred_live_rel": c.get("inferred_live_rel"),
                "score": c["score"],
            }) + "\n")

    prom_path = OUT / "dest_empty_promotable.jsonl"
    with open(prom_path, "w", encoding="utf-8") as f:
        for c in sorted(dest_empty, key=lambda x: (PRIORITY_EXT.get(x["ext"], 99), x["score"])):
            f.write(json.dumps({
                "hash": c["hash"],
                "size": c["size"],
                "src": c["path"],
                "inferred_live_rel": c["inferred_live_rel"],
                "gold_rel": c["inferred_live_rel"],
                "ext": c["ext"],
            }) + "\n")

    # skipped_heavy.txt
    with open(OUT / "skipped_heavy.txt", "w", encoding="utf-8") as f:
        f.write("Skipped heavy / non-interesting counts\n")
        for k, v in sorted(skipped_heavy.items(), key=lambda x: -x[1]):
            f.write(f"{k}: {v}\n")
        f.write(f"\nerrors: {len(errors)}\n")
        for e in errors[:100]:
            f.write(f"ERR: {e}\n")

    # --- Phase 4: copy to gold ---
    log("PHASE4: copy dest_empty_unique + high-value orphans to gold")
    copied = 0
    copied_bytes = 0
    copy_stopped = False
    copy_log = []

    # sort: .py/.ts first
    to_copy = sorted(dest_empty, key=lambda x: (PRIORITY_EXT.get(x["ext"], 99), x["score"]))

    # high-value unique_orphan .py
    orphan_py = [c for c in orphans if c["ext"] == ".py"]
    orphan_py.sort(key=lambda x: x["score"])

    def copy_one(src: Path, dest: Path, meta: dict) -> bool:
        nonlocal copied, copied_bytes, copy_stopped
        if copy_stopped:
            return False
        if copied_bytes + meta["size"] > CAP_BYTES:
            copy_stopped = True
            log(f"  CAP reached ({CAP_BYTES} bytes); stopping copies")
            return False
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists() and dest.stat().st_size > 0:
                # already there - skip
                return False
            shutil.copy2(src, dest)
            copied += 1
            copied_bytes += meta["size"]
            copy_log.append(str(dest))
            return True
        except OSError as e:
            errors.append(f"copy {src} -> {dest}: {e}")
            return False

    for c in to_copy:
        gold_dest = GOLD / c["inferred_live_rel"]
        copy_one(Path(c["path"]), gold_dest, c)

    orphan_copied = 0
    for c in orphan_py:
        if copy_stopped:
            break
        # shelf under orphans/ with flattened-ish path
        safe = c["rel_from_arch"].replace(":", "_").replace("..", "_")
        gold_dest = GOLD / "orphans" / safe
        if copy_one(Path(c["path"]), gold_dest, c):
            orphan_copied += 1

    # top 20 interesting
    top20 = sorted(candidates.values(), key=lambda x: (PRIORITY_EXT.get(x["ext"], 99), x["score"]))[:20]

    # MANIFEST.md
    total_unique_bytes = sum(c["size"] for c in candidates.values())
    dest_empty_bytes = sum(c["size"] for c in dest_empty)
    by_ext = defaultdict(int)
    for c in candidates.values():
        by_ext[c["ext"]] += 1

    manifest = OUT / "MANIFEST.md"
    with open(manifest, "w", encoding="utf-8") as f:
        f.write("# Final Gold Archaeology — 2026-09-13\n\n")
        f.write("Static unique-hash pass of D: archives vs live `C:\\RealAI-clean`.\n")
        f.write("NO deletes. Shelf only. Promote later after review.\n\n")
        f.write("## Counts\n\n")
        f.write(f"- Live files hashed: **{live_count}** ({len(live_hashes)} unique hashes)\n")
        f.write(f"- Archive files scanned (interesting): **{scanned}**\n")
        f.write(f"- Dup of live (skipped): **{dup_of_live}**\n")
        f.write(f"- Unique candidate hashes: **{len(candidates)}** ({total_unique_bytes:,} bytes)\n")
        f.write(f"- dest_empty_unique: **{len(dest_empty)}** ({dest_empty_bytes:,} bytes)\n")
        f.write(f"- unique_orphan: **{len(orphans)}**\n")
        f.write(f"- Copied to gold shelf: **{copied}** files, **{copied_bytes:,}** bytes")
        if copy_stopped:
            f.write(" (CAP HIT — stopped early)")
        f.write("\n")
        f.write(f"- Orphan .py copied under gold/orphans: **{orphan_copied}**\n")
        f.write(f"- Errors/inaccessible: **{len(errors)}**\n\n")
        f.write("## By extension (unique candidates)\n\n")
        for ext, n in sorted(by_ext.items(), key=lambda x: -x[1]):
            f.write(f"- `{ext}`: {n}\n")
        f.write("\n## How to use the shelf\n\n")
        f.write("1. Review `dest_empty_promotable.jsonl` — each row has `inferred_live_rel`.\n")
        f.write("2. After review, copy from `C:\\RealAI-gold\\<rel>` → `C:\\RealAI-clean\\<rel>` only if still dest-empty.\n")
        f.write("3. Orphans under `C:\\RealAI-gold\\orphans\\` need manual placement.\n")
        f.write("4. Do NOT wholesale-promote nested Recovery/grok_export trees.\n\n")
        f.write("## Top interesting unique paths\n\n")
        for i, c in enumerate(top20, 1):
            f.write(f"{i}. `{c['class']}` {c['ext']} {c['size']}B — `{c['path']}`")
            if c.get("inferred_live_rel"):
                f.write(f" → `{c['inferred_live_rel']}`")
            f.write("\n")
        f.write("\n## Outputs\n\n")
        f.write("- `live_hashes.jsonl`\n")
        f.write("- `unique_candidates.jsonl`\n")
        f.write("- `dest_empty_promotable.jsonl`\n")
        f.write("- `skipped_heavy.txt`\n")
        f.write("- `scan_log.txt`\n")
        f.write("- Shelf: `C:\\RealAI-gold\\`\n")

    # summary json for parent
    summary = {
        "live_files": live_count,
        "live_unique_hashes": len(live_hashes),
        "scanned": scanned,
        "dup_of_live": dup_of_live,
        "unique_hashes": len(candidates),
        "dest_empty": len(dest_empty),
        "orphans": len(orphans),
        "copied": copied,
        "copied_bytes": copied_bytes,
        "orphan_py_copied": orphan_copied,
        "copy_stopped_cap": copy_stopped,
        "errors": len(errors),
        "top20": [{"path": c["path"], "class": c["class"], "ext": c["ext"], "size": c["size"], "live_rel": c.get("inferred_live_rel")} for c in top20],
        "manifest": str(manifest),
        "gold": str(GOLD),
    }
    with open(OUT / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    log(f"DONE copied={copied} bytes={copied_bytes} dest_empty={len(dest_empty)} unique={len(candidates)}")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
