#!/usr/bin/env python3
"""Deep promote scan — find unique / richer / different code in named roots + nests.

Walks product-named folders and weird nested places, compares AST symbols
(functions/classes) against live authority destinations, and writes a promote
queue RealAI craft/heal can act on.

  python scripts/deep_promote_scan.py
  python scripts/deep_promote_scan.py --wire-thin   # also run deep_promote_wire

No deletes. No secret promotion. Skips C__* / node_modules / venv noise.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "scan_results"
OUT_JSON = OUT_DIR / "DEEP_PROMOTE_MAP.json"
OUT_MD = OUT_DIR / "DEEP_PROMOTE_MAP.md"
OUT_QUEUE = OUT_DIR / "deep_promote_queue.json"

# Live authority destinations (basename → preferred relative dirs, first wins for compare)
AUTHORITY_DIRS = [
    ROOT / "abilities",
    ROOT / "abilities" / "rackup",
    ROOT / "core",
    ROOT / "core" / "orchestration",
    ROOT / "core" / "agents",
    ROOT / "core" / "tools",
    ROOT / "core" / "web3",
    ROOT / "core" / "voice",
    ROOT / "core" / "training",
    ROOT / "modules",
    ROOT / "modules" / "organs",
    ROOT / "modules" / "desktop_unique",
    ROOT / "modules" / "agents_advanced",
    ROOT / "modules" / "self_improvement",
    ROOT / "modules" / "orchestrators",
    ROOT / "plugins" / "rackup_coach",
    ROOT / "plugins" / "rackup_coach" / "abilities",
    ROOT / "agent_tools",
    ROOT / "agent_tools" / "engine",
    ROOT / "agent_tools" / "tooling",
    ROOT / "agent_tools" / "providers",
    ROOT / "server",
    ROOT / "adapters",
    ROOT / "tools",
    ROOT / "training",
    ROOT / "realai",  # top-level only handled specially
]

# Named product roots to scan deeply (relative to ROOT)
NAMED_ROOTS = [
    "abilities",
    "adapters",
    "agent_tools",
    "agents",
    "aura",
    "benchmarks",
    "core",
    "modules",
    "plugins",
    "server",
    "tools",
    "training",
    "packages",
    "registry",
    "scanners",
    "scripts",
    "imports",
    "imports/external/unique-modules",
    "imports/external/agent_tools_gold",
    "imports/external/C_realai_modules",
    "imports/external/C_realai_plugins",
    "imports/external/orchestrators",
    "imports/external/self_improvement",
    "imports/external/organs",
    "imports/external/recovery_plugins",
    "docs",
    "apps",
    "realai",
]

SKIP_DIR_NAMES = {
    "node_modules",
    "node_modules.disabled",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".cache",
    "site-packages",
    "dist",
    "build",
    ".eggs",
    ".next",
    ".vs",
    "Output",
    ".kilo",
    "worktrees",
    "checkpoints_lora",
}

SKIP_NAME_PREFIXES = ("C__", "C_Users_", "_Users_", "Users_tsmit_")
SKIP_NAME_CONTAINS = ("node_modules", "package-lock", "pnpm-lock")

# Nest / weird dirs under realai that often hold alternate implementations
NEST_HINT_RE = re.compile(
    r"(gold|recovery|recycle|grok_export|from[-_]|cotton|HOMEPC|clean_backup|"
    r"realai-clean|orchestration|hierarchical|plugins[/\\]abilities|"
    r"plugins[/\\]tools|agent_tools_gold|from_desktop|RealAI_Recovery)",
    re.I,
)

SIGNAL_NAMES = {
    "orchestrat",
    "ability",
    "plugin",
    "agent",
    "self_heal",
    "self_improve",
    "self_builder",
    "world_model",
    "message_bus",
    "multi_agent",
    "web3",
    "solana",
    "rackup",
    "coach",
    "tournament",
    "ledger",
    "organ",
    "lora",
    "finetune",
    "mcp",
    "craft",
    "promote",
    "router",
    "overmind",
    "guardian",
    "doctor",
}


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def should_skip_dir(name: str) -> bool:
    if name in SKIP_DIR_NAMES:
        return True
    if name.startswith(SKIP_NAME_PREFIXES):
        return True
    if any(x in name for x in SKIP_NAME_CONTAINS):
        return True
    return False


def should_skip_file(path: Path) -> bool:
    name = path.name
    if path.suffix.lower() not in {".py", ".ts", ".js", ".md"}:
        return True
    if name.startswith(SKIP_NAME_PREFIXES):
        return True
    if any(x in name for x in SKIP_NAME_CONTAINS):
        return True
    if name in {"package-lock.json", "pnpm-lock.yaml"}:
        return True
    return False


def extract_symbols(path: Path) -> Dict[str, Any]:
    """Return functions/classes/async and rough sizes from a Python file."""
    out: Dict[str, Any] = {
        "functions": [],
        "async_functions": [],
        "classes": [],
        "methods": [],
        "parse_ok": False,
        "bytes": 0,
        "sha256": None,
        "signal_hits": [],
    }
    try:
        raw = path.read_bytes()
    except OSError:
        return out
    out["bytes"] = len(raw)
    out["sha256"] = sha256_bytes(raw)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
    lowered = text.lower()
    out["signal_hits"] = sorted({s for s in SIGNAL_NAMES if s in lowered})
    if path.suffix.lower() != ".py":
        # non-py: basename + signals only
        return out
    try:
        tree = ast.parse(text)
        out["parse_ok"] = True
    except SyntaxError:
        return out

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            out["functions"].append(node.name)
        elif isinstance(node, ast.AsyncFunctionDef):
            out["async_functions"].append(node.name)
        elif isinstance(node, ast.ClassDef):
            out["classes"].append(node.name)
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out["methods"].append(f"{node.name}.{item.name}")
    return out


def symbol_set(sym: Dict[str, Any]) -> Set[str]:
    return set(sym.get("functions") or []) | set(sym.get("async_functions") or []) | set(
        sym.get("classes") or []
    )


def is_under_realai_top_level(path: Path) -> bool:
    """True if file is directly under realai/ (not a nest subdir package dump)."""
    try:
        rel = path.relative_to(ROOT / "realai")
    except ValueError:
        return False
    return len(rel.parts) == 1 and rel.suffix == ".py"


def classify_nestiness(path: Path) -> str:
    try:
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        rel = str(path)
    if "/imports/" in f"/{rel}" or rel.startswith("imports/"):
        return "import_snapshot"
    if NEST_HINT_RE.search(rel):
        return "nest_or_gold"
    if rel.startswith("realai/") and not is_under_realai_top_level(path):
        # deeper under realai — could be live package (api/, cli/) or nest
        parts = Path(rel).parts
        if len(parts) >= 2 and parts[1] in {
            "api",
            "cli",
            "server",
            "agent_runtime",
            "abilities",
            "training",
            "providers",
            "plugins",
            "memory",
            "world_model",
            "config",
            "sdk",
            "routes",
            "schemas",
            "security",
            "skills",
            "tests",
            "voice",
            "web3",
            "engine",
            "inference",
            "logging",
            "metrics",
            "middleware",
            "models",
            "registry",
            "runtime",
            "tooling",
            "agents",
            "aura",
            "benchmarks",
            "components",
            "docs",
            "examples",
            "frontend",
            "hierarchical_agent_gold",
            "orchestration_gold",
            "agent_tools_gold",
            "realai_agent",
            "realai_orchestration_gold",
        }:
            if parts[1].endswith("_gold") or parts[1] in {
                "hierarchical_agent_gold",
                "orchestration_gold",
                "agent_tools_gold",
                "realai_orchestration_gold",
            }:
                return "gold_package"
            if parts[1] == "plugins" and len(parts) >= 3 and parts[2] in {
                "abilities",
                "tools",
                "atomic_fizz_realai",
            }:
                return "mis_homed_or_plugin"
            return "live_package"
        return "nest_or_gold"
    return "product"


def find_authority_matches(basename: str) -> List[Path]:
    """Find same-basename files under authority dirs + realai top-level."""
    hits: List[Path] = []
    seen: Set[Path] = set()
    for d in AUTHORITY_DIRS:
        if not d.is_dir():
            continue
        # Only immediate children for authority compare (avoid scanning nests as authority)
        if d.name == "realai" and d.parent == ROOT:
            for p in d.glob("*.py"):
                if p.name == basename and p not in seen:
                    hits.append(p)
                    seen.add(p)
            continue
        for p in d.glob(basename):
            if p.is_file() and p not in seen:
                hits.append(p)
                seen.add(p)
        # one level of subpackages for core/modules/plugins abilities
        for sub in d.iterdir() if d.is_dir() else []:
            if not sub.is_dir() or should_skip_dir(sub.name):
                continue
            cand = sub / basename
            if cand.is_file() and cand not in seen:
                hits.append(cand)
                seen.add(cand)
    # also root-level twin
    root_twin = ROOT / basename
    if root_twin.is_file() and root_twin not in seen:
        hits.append(root_twin)
    return hits


def propose_dest(path: Path, kind: str, signals: List[str]) -> Dict[str, str]:
    """Suggest live destination family for a candidate."""
    name = path.name
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    stem = path.stem.lower()

    if "rackup" in rel or stem in {
        "coach",
        "tournament",
        "ledger_audit",
        "matchmaking",
        "rating_update",
        "shot_of_the_day",
        "video_analysis",
        "pyramid_rules",
        "rating_intel",
        "moderation",
        "money_anomaly",
        "payout_sanity",
        "sotd_contribute",
        "hall_context",
        "league_validate",
        "rating_convert",
        "player_card_sync",
    }:
        return {
            "family": "abilities/rackup",
            "mode": "thin_wrap",
            "dest": f"abilities/rackup/{name}",
            "source_module": "plugins.rackup_coach.abilities." + path.stem,
        }

    if any(s in stem for s in ("organ",)) or "/organs/" in rel:
        return {"family": "modules/organs", "mode": "keep_or_ability", "dest": "abilities/organs_hive.py"}

    if "desktop_unique" in rel or stem.startswith("lambda_"):
        return {
            "family": "modules/desktop_unique",
            "mode": "thin_wrap_ability",
            "dest": f"abilities/desktop_{path.stem}.py",
            "source_module": f"modules.desktop_unique.{path.stem}",
        }

    if stem in {"overmind_runner", "code_engineer_agent"} or "agents_advanced" in rel:
        return {
            "family": "modules/agents_advanced",
            "mode": "thin_wrap_ability",
            "dest": f"abilities/{path.stem}.py",
            "source_module": f"modules.agents_advanced.{path.stem}",
        }

    if stem.startswith("orchestrator_") or stem in {
        "orchestrator_router",
        "orchestrator_overmind_runner",
        "orchestrator_self_improvement",
        "orchestrator_solana",
        "orchestrator_orchestration",
    }:
        return {
            "family": "modules/orchestrators",
            "mode": "exportable_or_module",
            "dest": f"modules/orchestrators/{name}",
        }

    if any(x in signals for x in ("web3", "solana")):
        return {"family": "core/web3", "mode": "review_diff", "dest": f"core/web3/{name}"}

    if any(x in signals for x in ("self_heal", "self_improve", "self_builder")):
        return {"family": "realai_top", "mode": "review_diff", "dest": f"realai/{name}"}

    if "plugin" in signals or "/plugins/tools/" in rel:
        return {
            "family": "plugins/tools",
            "mode": "review_keep",
            "dest": f"realai/plugins/tools/{name}",
        }

    if kind in {"UNIQUE", "RICHER"}:
        return {"family": "scripts/exportable", "mode": "exportable", "dest": f"scripts/exportable/{name}"}

    return {"family": "review", "mode": "review", "dest": rel}


def iter_scan_files() -> Iterable[Path]:
    for named in NAMED_ROOTS:
        base = ROOT / named
        if not base.exists():
            continue
        # Cap apps/frontend depth — only scan shallow source, skip node_modules already
        if named == "apps":
            for sub in ("desktop", "api", "dashboard", "fusion-ui", "widget", "vscode/src"):
                p = base / sub
                if not p.exists():
                    continue
                for f in p.rglob("*"):
                    if f.is_dir():
                        continue
                    # skip deep vscode node bits
                    if "node_modules" in f.parts:
                        continue
                    if should_skip_file(f):
                        continue
                    yield f
            continue

        for dirpath, dirnames, filenames in _walk(base):
            for fn in filenames:
                f = Path(dirpath) / fn
                if should_skip_file(f):
                    continue
                yield f


def _walk(base: Path):
    """os.walk-like with dir pruning."""
    import os

    for dirpath, dirnames, filenames in os.walk(base):
        # prune in-place
        pruned = []
        for d in list(dirnames):
            if should_skip_dir(d):
                continue
            # skip enormous frontend under realai/frontend
            if d in {"frontend", "fusion-ui"} and "realai" in Path(dirpath).parts:
                # still allow but skip node_modules already; skip if path deep
                pass
            pruned.append(d)
        dirnames[:] = pruned
        yield dirpath, dirnames, filenames


def build_authority_index() -> Dict[str, List[Dict[str, Any]]]:
    """basename → list of authority file symbol records."""
    idx: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    files: List[Path] = []
    for d in AUTHORITY_DIRS:
        if not d.exists():
            continue
        if d.name == "realai" and d.parent == ROOT:
            files.extend(p for p in d.glob("*.py") if p.is_file())
            continue
        for p in d.rglob("*.py"):
            if any(should_skip_dir(part) for part in p.parts):
                continue
            if any(part.startswith(SKIP_NAME_PREFIXES) for part in p.parts):
                continue
            # don't treat nest dumps under realai as authority except gold packages lightly
            try:
                rel_parts = p.relative_to(ROOT).parts
            except ValueError:
                continue
            if len(rel_parts) >= 2 and rel_parts[0] == "realai":
                # only top-level and known live packages as authority
                if len(rel_parts) == 2:
                    pass
                elif rel_parts[1] in {
                    "api",
                    "cli",
                    "server",
                    "agent_runtime",
                    "abilities",
                    "training",
                    "providers",
                    "config",
                    "sdk",
                    "routes",
                    "schemas",
                    "security",
                    "skills",
                    "tests",
                    "voice",
                    "web3",
                    "engine",
                    "inference",
                    "logging",
                    "metrics",
                    "middleware",
                    "models",
                    "registry",
                    "runtime",
                    "tooling",
                    "agents",
                    "plugins",
                }:
                    if any(x.startswith(SKIP_NAME_PREFIXES) for x in rel_parts):
                        continue
                    if "plugins" in rel_parts and any(
                        x.startswith(("C__", "from-", "HOMEPC", "clean_backup")) for x in rel_parts
                    ):
                        continue
                else:
                    continue
            files.append(p)

    for p in files:
        sym = extract_symbols(p)
        idx[p.name].append(
            {
                "path": str(p.relative_to(ROOT)).replace("\\", "/"),
                "symbols": sorted(symbol_set(sym)),
                "bytes": sym["bytes"],
                "sha256": sym["sha256"],
                "signal_hits": sym["signal_hits"],
            }
        )
    return idx


def compare_candidate(
    path: Path, auth_idx: Dict[str, List[Dict[str, Any]]]
) -> Optional[Dict[str, Any]]:
    nestiness = classify_nestiness(path)
    # Always consider nest/gold/import/mis-homed; for product files only if under named roots with signals
    if nestiness == "product" and path.suffix != ".py":
        return None

    sym = extract_symbols(path)
    cand_set = symbol_set(sym)
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    auth_list = auth_idx.get(path.name, [])

    # Skip comparing a file against itself
    auth_list = [a for a in auth_list if a["path"] != rel]
    rec: Dict[str, Any] = {
        "path": rel,
        "basename": path.name,
        "nestiness": nestiness,
        "bytes": sym["bytes"],
        "sha256": sym["sha256"],
        "symbols": sorted(cand_set),
        "symbol_count": len(cand_set),
        "signal_hits": sym["signal_hits"],
        "parse_ok": sym["parse_ok"],
    }

    if not auth_list:
        if path.suffix != ".py":
            if not sym["signal_hits"]:
                return None
            rec["kind"] = "DOC_SIGNAL"
            rec["action"] = "index"
            return rec
        if not cand_set and not sym["signal_hits"]:
            return None
        # unique basename
        if sym["bytes"] < 80:
            rec["kind"] = "EMPTY_OR_TINY"
            rec["action"] = "ignore"
            return rec
        rec["kind"] = "UNIQUE"
        rec["action"] = "promote_or_export"
        rec["proposal"] = propose_dest(path, "UNIQUE", sym["signal_hits"])
        return rec

    # pick best authority (largest symbol set, then bytes)
    best = max(auth_list, key=lambda a: (len(a["symbols"]), a["bytes"]))
    auth_set = set(best["symbols"])
    rec["authority"] = best["path"]
    rec["authority_symbols"] = best["symbols"]
    rec["authority_bytes"] = best["bytes"]

    if best.get("sha256") and best["sha256"] == sym["sha256"]:
        rec["kind"] = "IDENTICAL"
        rec["action"] = "archive_later"
        return rec

    only_cand = sorted(cand_set - auth_set)
    only_auth = sorted(auth_set - cand_set)
    rec["only_in_candidate"] = only_cand
    rec["only_in_authority"] = only_auth

    if len(cand_set) > len(auth_set) and only_cand:
        rec["kind"] = "RICHER"
        rec["action"] = "review_merge_or_wrap"
        rec["proposal"] = propose_dest(path, "RICHER", sym["signal_hits"])
        return rec

    if only_cand and nestiness in {"nest_or_gold", "gold_package", "import_snapshot", "mis_homed_or_plugin"}:
        rec["kind"] = "DIFFERENT"
        rec["action"] = "review_diff"
        rec["proposal"] = propose_dest(path, "DIFFERENT", sym["signal_hits"])
        return rec

    if nestiness == "mis_homed_or_plugin" and path.parent.name == "abilities":
        # rackup abilities mis-homed — always queue for thin wrap if not already under abilities/rackup
        live_wrap = ROOT / "abilities" / "rackup" / path.name
        if not live_wrap.is_file() and path.suffix == ".py" and path.name != "__init__.py":
            rec["kind"] = "MIS_HOMED_ABILITY"
            rec["action"] = "thin_wrap"
            rec["proposal"] = propose_dest(path, "UNIQUE", sym["signal_hits"])
            return rec

    if only_cand:
        rec["kind"] = "DIFFERENT"
        rec["action"] = "review_diff"
        rec["proposal"] = propose_dest(path, "DIFFERENT", sym["signal_hits"])
        return rec

    # different bytes but same symbols — prefer newer/live
    if sym["bytes"] != best["bytes"]:
        rec["kind"] = "SAME_SYMBOLS_DIFF_BYTES"
        rec["action"] = "keep_authority" if best["bytes"] >= sym["bytes"] else "review_size"
        return rec

    rec["kind"] = "NEAR_DUP"
    rec["action"] = "ignore"
    return rec


NOISE_BASENAME_RE = re.compile(
    r"^(plugin_test_realai|plugin___init__|New Python|test_realai)(_\d+)?\.py$",
    re.I,
)
NUMBERED_TWIN_RE = re.compile(r"^(.+)_(\d+)\.py$", re.I)


def is_noise_path(rel: str, basename: str) -> bool:
    if NOISE_BASENAME_RE.match(basename):
        return True
    parts = rel.replace("\\", "/").split("/")
    if any(p.startswith(SKIP_NAME_PREFIXES) for p in parts):
        return True
    # self-nests / promote junk
    if "/plugins/plugins/" in f"/{rel}" or "/tools/tools/" in f"/{rel}":
        return True
    if "/_archive_nest/" in f"/{rel}":
        return True
    # HOMEPC dated single-file forks under agent_runtime — noise once package exists
    if "HOMEPC" in rel or "clean_backup_" in rel:
        return True
    return False


def score_item(item: Dict[str, Any]) -> int:
    kind = item.get("kind") or ""
    base = {
        "MIS_HOMED_ABILITY": 100,
        "RICHER": 90,
        "UNIQUE": 80,
        "DIFFERENT": 70,
        "DOC_SIGNAL": 20,
        "SAME_SYMBOLS_DIFF_BYTES": 15,
        "IDENTICAL": 0,
        "EMPTY_OR_TINY": 0,
        "NEAR_DUP": 0,
    }.get(kind, 10)
    base += min(30, int(item.get("symbol_count") or 0))
    base += min(20, len(item.get("signal_hits") or []) * 3)
    base += min(20, len(item.get("only_in_candidate") or []) * 2)
    if item.get("nestiness") in {"nest_or_gold", "gold_package", "mis_homed_or_plugin"}:
        base += 10
    rel = str(item.get("path") or "")
    # prefer gold packages and modules/ over deep dated nests
    if "/hierarchical_agent_gold/" in rel or "/orchestration_gold/" in rel:
        base += 25
    if rel.startswith("modules/") or rel.startswith("plugins/rackup_coach/"):
        base += 20
    if rel.startswith("imports/external/"):
        base += 5
    if is_noise_path(rel, str(item.get("basename") or "")):
        base -= 80
    # demote false RICHER where candidate IS the live package path
    if kind == "RICHER" and (
        rel.startswith("realai/agent_runtime/agent_runtime.py")
        or rel == "realai/__init__.py"
        or rel == "realai/cli/craft.py"
        or rel == "server/router.py"
    ):
        base -= 40
    return base


def write_md(report: Dict[str, Any]) -> None:
    lines = [
        "# DEEP_PROMOTE_MAP — named roots + nests",
        "",
        f"Generated: `{report['generated']}`",
        f"Scanned files: **{report['scanned_files']}** · actionable: **{report['actionable_count']}**",
        "",
        "## How to use",
        "",
        "```bat",
        "python scripts\\deep_promote_scan.py",
        "python scripts\\deep_promote_wire.py --dry-run",
        "python scripts\\deep_promote_wire.py",
        "```",
        "",
        "Craft/dispatch keywords: `deep promote`, `promote deep`, `nested gold`.",
        "",
        "## Top actionable (by score)",
        "",
        "| Score | Kind | Action | Path | Proposal | Extra symbols |",
        "|------:|------|--------|------|----------|---------------|",
    ]
    for item in report["top"]:
        prop = item.get("proposal") or {}
        extra = ", ".join((item.get("only_in_candidate") or [])[:6])
        lines.append(
            f"| {item.get('score', 0)} | `{item.get('kind')}` | `{item.get('action')}` | "
            f"`{item.get('path')}` | `{prop.get('mode', '')}` → `{prop.get('dest', '')}` | {extra} |"
        )

    lines += ["", "## Counts by kind", "", "| Kind | Count |", "|------|------:|"]
    for k, v in sorted(report["by_kind"].items(), key=lambda kv: -kv[1]):
        lines.append(f"| `{k}` | {v} |")

    lines += [
        "",
        "## Counts by nestiness",
        "",
        "| Nestiness | Count |",
        "|-----------|------:|",
    ]
    for k, v in sorted(report["by_nestiness"].items(), key=lambda kv: -kv[1]):
        lines.append(f"| `{k}` | {v} |")

    lines += [
        "",
        "## Queue families (promote destinations)",
        "",
    ]
    for fam, items in report.get("by_family", {}).items():
        lines.append(f"### `{fam}` ({len(items)})")
        for it in items[:15]:
            lines.append(f"- `{it['path']}` — {it.get('kind')} / {it.get('action')}")
        if len(items) > 15:
            lines.append(f"- … +{len(items) - 15} more")
        lines.append("")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wire-thin", action="store_true", help="Run deep_promote_wire after scan")
    ap.add_argument("--limit", type=int, default=0, help="Debug: stop after N files")
    args = ap.parse_args()

    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("[deep_promote_scan] building authority index…", flush=True)
    auth_idx = build_authority_index()
    print(f"[deep_promote_scan] authority basenames={len(auth_idx)}", flush=True)

    findings: List[Dict[str, Any]] = []
    scanned = 0
    for path in iter_scan_files():
        scanned += 1
        if args.limit and scanned > args.limit:
            break
        if scanned % 2000 == 0:
            print(f"[deep_promote_scan] scanned={scanned} findings={len(findings)}", flush=True)
        try:
            rec = compare_candidate(path, auth_idx)
        except Exception as e:
            findings.append(
                {
                    "path": str(path),
                    "kind": "ERROR",
                    "action": "ignore",
                    "error": str(e)[:200],
                    "score": 0,
                }
            )
            continue
        if not rec:
            continue
        # Drop pure identical/noise from primary list unless mis-homed
        if rec.get("kind") in {"IDENTICAL", "NEAR_DUP", "EMPTY_OR_TINY"} and rec.get(
            "action"
        ) != "thin_wrap":
            continue
        if is_noise_path(str(rec.get("path") or ""), str(rec.get("basename") or "")):
            continue
        # skip numbered recycle twins when canonical basename also exists nearby
        m = NUMBERED_TWIN_RE.match(str(rec.get("basename") or ""))
        if m and rec.get("kind") == "UNIQUE":
            continue
        rec["score"] = score_item(rec)
        if int(rec["score"]) < 40:
            continue
        findings.append(rec)

    # Also explicitly scan plugins/rackup_coach/abilities for missing wraps
    rackup_ab = ROOT / "plugins" / "rackup_coach" / "abilities"
    if rackup_ab.is_dir():
        for p in rackup_ab.glob("*.py"):
            if p.name == "__init__.py":
                continue
            wrap = ROOT / "abilities" / "rackup" / p.name
            if wrap.is_file():
                continue
            # ensure in findings
            if any(f.get("path", "").endswith(f"rackup_coach/abilities/{p.name}") for f in findings):
                continue
            sym = extract_symbols(p)
            findings.append(
                {
                    "path": str(p.relative_to(ROOT)).replace("\\", "/"),
                    "basename": p.name,
                    "nestiness": "mis_homed_or_plugin",
                    "bytes": sym["bytes"],
                    "symbols": sorted(symbol_set(sym)),
                    "symbol_count": len(symbol_set(sym)),
                    "signal_hits": sym["signal_hits"],
                    "kind": "MIS_HOMED_ABILITY",
                    "action": "thin_wrap",
                    "proposal": propose_dest(p, "UNIQUE", sym["signal_hits"]),
                    "score": 120,
                }
            )

    findings.sort(key=lambda x: (-int(x.get("score") or 0), x.get("path") or ""))

    # Dedupe by (basename, sha256) keeping best score / shortest product-like path
    deduped: List[Dict[str, Any]] = []
    seen_hash: Set[Tuple[str, str]] = set()
    for f in findings:
        key = (str(f.get("basename") or ""), str(f.get("sha256") or f.get("path")))
        if key in seen_hash and f.get("kind") != "MIS_HOMED_ABILITY":
            continue
        seen_hash.add(key)
        deduped.append(f)
    findings = deduped

    by_kind: Dict[str, int] = defaultdict(int)
    by_nest: Dict[str, int] = defaultdict(int)
    by_family: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    actionable = []
    for f in findings:
        by_kind[str(f.get("kind"))] += 1
        by_nest[str(f.get("nestiness") or "?")] += 1
        if f.get("action") in {
            "thin_wrap",
            "promote_or_export",
            "review_merge_or_wrap",
            "review_diff",
            "exportable_or_module",
        }:
            actionable.append(f)
            fam = (f.get("proposal") or {}).get("family") or "review"
            by_family[fam].append(f)

    queue = {
        "generated": utc(),
        "policy": "thin_wrap_preferred; no bulk nest delete; no secrets",
        "items": [
            {
                "id": f"{f.get('kind')}:{f.get('basename')}",
                "path": f.get("path"),
                "kind": f.get("kind"),
                "action": f.get("action"),
                "score": f.get("score"),
                "proposal": f.get("proposal"),
                "only_in_candidate": f.get("only_in_candidate"),
                "authority": f.get("authority"),
            }
            for f in actionable[:200]
        ],
    }

    report = {
        "generated": utc(),
        "root": str(ROOT),
        "duration_s": round(time.time() - t0, 2),
        "scanned_files": scanned,
        "findings_count": len(findings),
        "actionable_count": len(actionable),
        "by_kind": dict(by_kind),
        "by_nestiness": dict(by_nest),
        "by_family": {k: v[:40] for k, v in by_family.items()},
        "top": findings[:80],
        "queue_path": str(OUT_QUEUE.relative_to(ROOT)).replace("\\", "/"),
    }

    OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    OUT_QUEUE.write_text(json.dumps(queue, indent=2), encoding="utf-8")
    write_md(report)

    print(
        f"[deep_promote_scan] done scanned={scanned} findings={len(findings)} "
        f"actionable={len(actionable)} → {OUT_MD}",
        flush=True,
    )

    if args.wire_thin:
        from subprocess import run

        wire = ROOT / "scripts" / "deep_promote_wire.py"
        if wire.is_file():
            run(["python", str(wire)], check=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
