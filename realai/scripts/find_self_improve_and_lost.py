#!/usr/bin/env python3
"""Find self-improve / ability / orchestration candidates from repo scan + live good-code roots."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

SCAN_CANDIDATES = [
    Path("scripts") / "recovered" / "REALAI_REPO_SCAN.json",
    Path("recovered") / "REALAI_REPO_SCAN.json",
]

GOOD_CATALOG = [
    Path("scan_results") / "GOOD_CODE_ROOTS.json",
    Path("recovered") / "GOOD_CODE_ROOTS.json",
]

KEYWORDS = [
    "self_improve", "selfheal", "self-heal", "self_heal",
    "agent_runtime", "world_model", "aura_memory", "memory",
    "plugin", "plugins", "ability", "catalog",
    "orchestrator", "provider", "dispatcher",
    "dashboard", "ui", "vscode", "extension",
    "recovery", "wire_recovered", "promote", "registry",
    "tool", "organ", "rackup", "deep_promote",
    "specialist", "secure_tool", "approval", "device_selector",
    "hierarchical", "nest_orchestr", "hive",
]

# Fallback roots when scan JSON is missing/thin
FALLBACK_ROOTS = [
    "abilities",
    "adapters",
    "agent_tools",
    "core",
    "modules",
    "plugins",
    "realai",
    "imports/external/unique-modules",
    "imports/external/agent_tools_gold",
    "imports/external/C_realai_modules",
    "imports/external/orchestrators",
    "imports/external/self_improvement",
    "imports/external/recovery_plugins",
]


def _resolve_scan() -> Path | None:
    for p in SCAN_CANDIDATES:
        if p.is_file():
            return p
    return None


def _present_roots() -> list[Path]:
    for cat in GOOD_CATALOG:
        if not cat.is_file():
            continue
        try:
            data = json.loads(cat.read_text(encoding="utf-8"))
            roots = []
            for rel in data.get("present_roots") or []:
                p = Path(str(rel))
                if p.exists():
                    roots.append(p)
            if roots:
                return roots
        except Exception:
            continue
    return [Path(r) for r in FALLBACK_ROOTS if Path(r).exists()]


def _score_name(name: str, rel: str) -> int:
    score = 0
    blob = f"{name} {rel}".lower()
    for k in KEYWORDS:
        if k in blob:
            score += 2
    if name.endswith(".py"):
        score += 1
    return score


def _walk_roots(roots: list[Path]) -> list[dict]:
    hits: list[dict] = []
    skip = {"node_modules", ".venv", "venv", "__pycache__", ".git", "dist", "build"}
    for root in roots:
        if root.is_file():
            continue
        for p in root.rglob("*.py"):
            if any(part in skip for part in p.parts):
                continue
            try:
                rel = str(p.as_posix())
                name = p.name
            except Exception:
                continue
            score = _score_name(name, rel)
            if score < 2:
                continue
            try:
                size = p.stat().st_size
            except OSError:
                size = 0
            hits.append({
                "root": str(root),
                "rel": rel,
                "name": name,
                "score": score,
                "ext": p.suffix,
                "size": size,
                "source": "good_code_walk",
            })
    return hits


def _hits_from_scan(data) -> list[dict]:
    if isinstance(data, dict) and "roots" in data:
        repos = data["roots"]
    elif isinstance(data, list):
        repos = data
    else:
        return []

    hits = []
    for repo in repos:
        if isinstance(repo, str) or not isinstance(repo, dict):
            continue
        root = repo.get("root", "")
        files = repo.get("files", [])
        if isinstance(files, dict):
            files = list(files.values())
        for f in files:
            if isinstance(f, str):
                name = f.lower()
                rel = f.lower()
                score = 0
                ext = Path(f).suffix
                size = 0
                rel_out, name_out = f, Path(f).name
            elif isinstance(f, dict):
                try:
                    name = str(f.get("name", "")).lower()
                    rel = str(f.get("rel", "")).lower()
                    score = f.get("score", 0)
                    if not isinstance(score, (int, float)):
                        score = 0
                except Exception:
                    continue
                rel_out = f.get("rel", "")
                name_out = f.get("name", "")
                ext = f.get("ext", "")
                size = f.get("size", 0)
            else:
                continue

            if any(k in name or k in rel for k in KEYWORDS):
                hits.append({
                    "root": root,
                    "rel": rel_out,
                    "name": name_out,
                    "score": score,
                    "ext": ext,
                    "size": size,
                    "source": "repo_scan",
                })
    return hits


def main():
    hits: list[dict] = []
    scan = _resolve_scan()
    if scan is not None:
        try:
            data = json.loads(scan.read_text(encoding="utf-8"))
            hits.extend(_hits_from_scan(data))
            print(f"[lost] loaded scan {scan} → {len(hits)} keyword hits")
        except Exception as e:
            print("[lost] failed to read scan file:", e)
    else:
        print("[lost] scan file missing; tried:", [str(p) for p in SCAN_CANDIDATES])
        print("[lost] hint: run scripts/catalog_good_code_roots.py then scan_repos_for_realai.py")

    # Always enrich from live good-code roots so dispatch has places to get code
    walk_hits = _walk_roots(_present_roots())
    print(f"[lost] good-code walk → {len(walk_hits)} candidates")

    # Merge by rel, prefer higher score
    by_rel: dict[str, dict] = {}
    for h in hits + walk_hits:
        key = str(h.get("rel") or "").replace("\\", "/").lower()
        if not key:
            continue
        prev = by_rel.get(key)
        if prev is None or (h.get("score") or 0) >= (prev.get("score") or 0):
            by_rel[key] = h
    merged = list(by_rel.values())
    merged.sort(key=lambda x: x.get("score", 0), reverse=True)

    payload = json.dumps(merged, indent=2)
    outs = []
    for d in (Path("scripts") / "recovered", Path("recovered"), Path("scan_results")):
        try:
            d.mkdir(parents=True, exist_ok=True)
            out = d / "REALAI_SELF_IMPROVE_CANDIDATES.json"
            out.write_text(payload, encoding="utf-8")
            outs.append(str(out))
        except OSError as e:
            print("[lost] write failed", d, e)

    print(f"[lost] wrote {outs} ({len(merged)} candidates)")
    return 0 if merged else 1


if __name__ == "__main__":
    raise SystemExit(main() or 0)
