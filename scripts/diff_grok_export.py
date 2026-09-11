#!/usr/bin/env python3
"""Compare C:\\realai_grok_export vs C:\\RealAI-clean source trees (no copy)."""
from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path

EXPORT = Path(r"C:\realai_grok_export")
CLEAN = Path(r"C:\RealAI-clean")

SKIP_DIR_PARTS = {
    ".git",
    "node_modules",
    "node_modules.disabled",
    "__pycache__",
    ".next",
    "dist",
    "build",
    "logs",
    "terminals",
    "recovered",
    "realai_og_mess",
    "_hold_untracked_20260804_1007",
    "scan_results",
    "venv",
    ".venv",
    "archive",
}
SKIP_FILE_SUFFIX = {".pyc", ".pyo", ".map", ".gguf", ".sqlite3", ".sqlite", ".lock", ".png", ".jpg", ".wasm"}
SKIP_FILE_NAMES = {
    "repo_tree.txt",
    "repo_tree_clean.txt",
    "repo_tree_filtered.txt",
    "repo_tree_shallow.txt",
    "package-lock.json",
    "pnpm-lock.yaml",
    "tsconfig.tsbuildinfo",
}
SOURCE_SUFFIX = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".md",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".bat",
    ".cmd",
    ".ps1",
    ".sh",
    ".rs",
    ".go",
    ".sql",
    ".html",
    ".css",
    ".scss",
}


def should_skip(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    for part in rel.parts[:-1]:
        if part in SKIP_DIR_PARTS:
            return True
        if part.startswith(".") and part not in (".github",):
            return True
    if path.name in SKIP_FILE_NAMES:
        return True
    if path.suffix.lower() in SKIP_FILE_SUFFIX:
        return True
    return False


def is_source(path: Path) -> bool:
    if path.suffix.lower() in SOURCE_SUFFIX:
        return True
    if path.name in ("Dockerfile", "Dockerfile.gpu", "Makefile", "LICENSE"):
        return True
    return False


def collect(root: Path) -> dict:
    out: dict = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dpath = Path(dirpath)
        # prune
        keep = []
        for d in dirnames:
            if d in SKIP_DIR_PARTS:
                continue
            if d.startswith(".") and d not in (".github",):
                continue
            keep.append(d)
        dirnames[:] = keep
        for fn in filenames:
            p = dpath / fn
            if should_skip(p, root) or not is_source(p):
                continue
            rel = p.relative_to(root).as_posix()
            try:
                st = p.stat()
                h = None
                if st.st_size <= 2_000_000:
                    h = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
                out[rel] = {"size": st.st_size, "hash": h}
            except OSError:
                continue
    return out


def main() -> int:
    if not EXPORT.is_dir():
        print("Missing", EXPORT)
        return 1
    print("Scanning export...")
    exp = collect(EXPORT)
    print(" export source files", len(exp))
    print("Scanning clean...")
    cln = collect(CLEAN)
    print(" clean source files", len(cln))

    only_export = sorted(set(exp) - set(cln))
    only_clean = sorted(set(cln) - set(exp))
    both = sorted(set(exp) & set(cln))

    diff_content = []
    for rel in both:
        eh, ch = exp[rel].get("hash"), cln[rel].get("hash")
        if eh and ch and eh != ch:
            diff_content.append(rel)

    print(f"\n=== ONLY IN EXPORT (missing from clean): {len(only_export)}")
    by_top: dict[str, list] = defaultdict(list)
    for r in only_export:
        by_top[r.split("/")[0]].append(r)

    for top in sorted(by_top, key=lambda t: (-len(by_top[t]), t)):
        files = by_top[top]
        print(f"\n## {top}/  ({len(files)} files)")
        for r in files[:50]:
            print(f"  {r}  ({exp[r]['size']} bytes)")
        if len(files) > 50:
            print(f"  ... +{len(files) - 50} more")

    print(f"\n=== SAME PATH, DIFFERENT CONTENT: {len(diff_content)}")
    important_prefixes = (
        "realai/",
        "core/",
        "plugins/",
        "agents/",
        "apps/",
        "scripts/",
        "packages/",
        "providers/",
        "server/",
        "modules/",
        "aura/",
        "adapters/",
    )
    imp_diff = [
        r
        for r in diff_content
        if r.startswith(important_prefixes) or "/" not in r
    ]
    print(" important code diffs:", len(imp_diff))
    for r in imp_diff[:60]:
        print(f"  DIFF {r}  export={exp[r]['size']} clean={cln[r]['size']}")
    if len(imp_diff) > 60:
        print(f"  ... +{len(imp_diff) - 60} more")

    print(f"\n=== ONLY IN CLEAN (not in export): {len(only_clean)}")
    by_top2: dict[str, list] = defaultdict(list)
    for r in only_clean:
        by_top2[r.split("/")[0]].append(r)
    for top in sorted(by_top2, key=lambda t: (-len(by_top2[t]), t))[:20]:
        print(f"  {top}/ {len(by_top2[top])}")

    # Highlight high-value missing code (py/ts under product dirs)
    high = [
        r
        for r in only_export
        if r.endswith((".py", ".ts", ".tsx", ".js"))
        and r.split("/")[0]
        in {
            "realai",
            "realai-core",
            "core",
            "plugins",
            "agents",
            "apps",
            "packages",
            "providers",
            "scripts",
            "aura",
            "context",
            "vendor",
            "solana-client",
            "marketplace",
            "training",
            "tests",
            "api",
            "autopilot",
            "benchmarks",
            "billing",
            "config",
            "src",
        }
    ]
    print(f"\n=== HIGH-VALUE MISSING CODE (.py/.ts/.js in product dirs): {len(high)}")
    by_h: dict[str, list] = defaultdict(list)
    for r in high:
        by_h[r.split("/")[0]].append(r)
    for top in sorted(by_h, key=lambda t: (-len(by_h[t]), t)):
        print(f"\n### {top}/ ({len(by_h[top])})")
        for r in by_h[top][:30]:
            print(f"  {r}")
        if len(by_h[top]) > 30:
            print(f"  ... +{len(by_h[top]) - 30} more")

    report = {
        "export": str(EXPORT),
        "clean": str(CLEAN),
        "only_export_count": len(only_export),
        "only_clean_count": len(only_clean),
        "diff_content_count": len(diff_content),
        "high_value_missing": high,
        "only_export_by_top": {k: len(v) for k, v in sorted(by_top.items())},
        "only_export": only_export,
        "important_diffs": imp_diff,
    }
    outp = CLEAN / "scan_results" / "grok_export_diff.json"
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nWrote", outp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
