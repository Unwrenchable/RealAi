"""Canonical path per duplicated module (read-only; never moves files).

A *duplicate group* is two or more importable tracked ``*.py`` files with identical bytes
(>= 300 bytes, not ``__init__.py``) outside the parking shelves. For every group one path is
canonical. The rules come from prior cleanup work so this map cannot undo it:

  docs/AUTHORITY.md, docs/MONOREPO_TARGET_LAYOUT.md, scan_results/ONE_TREE.md (winner table),
  docs/NESTED_REALAI_PARK_AUDIT.md, _quarantine/twins_20260926/PHASE3_PARK.md.

Nothing here parks anything. Future moves out of C:\\RealAI-clean go to D:\\ARCHIVE
(see docs/CANONICAL_PATHS.md); in-repo shelves stay ``_quarantine/`` / ``_parked/``.

  python -m realai.repo_hygiene.canonical_paths            # print summary
  python -m realai.repo_hygiene.canonical_paths --write    # regenerate config/canonical_paths.json + docs
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
JSON_PATH = ROOT / "config" / "canonical_paths.json"
DOC_PATH = ROOT / "docs" / "CANONICAL_PATHS.md"
MIN_BYTES = 300
SHELF = re.compile(r"^(_quarantine|_parked|recovered|imports|archive|scan_results|node_modules)/|/node_modules/"
                   r"|(^|/)tests?/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)\.learn_cache/")

# (prefix, reason) in priority order. First match wins. Sources in the module docstring.
PRIOR_RULES: List[Tuple[str, str]] = [
    ("realai/orchestration/", "AUTHORITY.md: hive/bridge gold is realai/orchestration"),
    ("realai/plugins/rackup_coach/", "ONE_TREE winner: rackup_coach gold under realai/plugins (plugins/rackup_coach is a shim)"),
    ("realai/plugins/", "AUTHORITY.md: plugins are realai/plugins (NESTED_REALAI_PARK_AUDIT: coach.py etc. gold here)"),
    ("modules/organs/", "AUTHORITY.md: organs are modules/organs (realai/modules/organs parked 2026-09-24)"),
    ("realai/providers/", "AUTHORITY.md: provider config gold is realai/providers"),
    ("realai/server/", "ONE_TREE winner: server gold realai/server (server/* are shims)"),
    ("realai/core/", "MONOREPO_TARGET_LAYOUT: self_builder/self_heal/closed_loop gold is realai/core"),
    ("abilities/", "ONE_TREE winner: product-root abilities/ (realai/abilities is a compat shim, DO_NOT_PARK)"),
    ("agents/", "ONE_TREE winner: product-root agents/ (realai/agents parked 2b52297)"),
    ("agent_tools/", "NESTED_REALAI_PARK_AUDIT: live imports use agent_tools.* (realai/agent_tools_gold is the gold shelf twin)"),
    ("modules/orchestrators/", "MONOREPO_TARGET_LAYOUT: realai-worker entry modules/orchestrators"),
    ("modules/desktop_unique/", "PHASE3_PARK: catalog and hive use product-root modules/desktop_unique"),
]
# Inside abilities/: the rackup copies lose to realai/plugins (rackup gold), so abilities/rackup ranks after plugins.
DEMOTE = ("abilities/rackup/",)
# Snapshot / dump names never win (dated HOMEPC dirs, C_Users_* flattenings, __dupN, recycle_py, variants, _NN copies).
SNAPSHOT = re.compile(r"HOMEPC|C_Users_|C__|__dup\d|recycle_py|/variants/|from_desktop_missing|from_accident|"
                      r"-20\d{6}|_20\d{6}|realai_recovery_|_\d{1,3}\.py$|realai-ish|nested")


def tracked_py(root: Path = ROOT) -> List[str]:
    try:
        out = subprocess.check_output(["git", "ls-files", "*.py"], cwd=root, text=True, stderr=subprocess.DEVNULL)
        files = [f for f in out.splitlines() if f]
    except Exception:  # no git: walk the tree
        files = [p.relative_to(root).as_posix() for p in root.rglob("*.py")]
    return sorted(f for f in files if not SHELF.search(f) and (root / f).is_file())


def duplicate_groups(root: Path = ROOT) -> Dict[str, List[str]]:
    g: Dict[str, List[str]] = collections.defaultdict(list)
    for f in tracked_py(root):
        if f.endswith("__init__.py"):
            continue
        b = (root / f).read_bytes()
        if len(b) < MIN_BYTES:
            continue
        g[hashlib.sha256(b).hexdigest()].append(f)
    return {h: sorted(v) for h, v in g.items() if len(v) > 1}


def _importers(root: Path, files: List[str]) -> collections.Counter:
    """How many tracked files import each candidate's dotted name (cheap text scan)."""
    names = {}
    for f in files:
        mod = f[:-3].replace("/", ".")
        names[f] = {mod, mod[len("realai."):] if mod.startswith("realai.") else mod}
    c: collections.Counter = collections.Counter()
    pat = {f: re.compile(r"(?:from|import)\s+(?:%s)\b" % "|".join(re.escape(n) for n in ns)) for f, ns in names.items()}
    for src in tracked_py(root):
        try:
            text = (root / src).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for f, p in pat.items():
            if src != f and p.search(text):
                c[f] += 1
    return c


def choose(paths: List[str], importers: Optional[collections.Counter] = None) -> Tuple[str, str]:
    for prefix, why in PRIOR_RULES:
        hits = [p for p in paths if p.startswith(prefix) and not p.startswith(DEMOTE) and not SNAPSHOT.search(p)]
        if hits:
            return sorted(hits, key=lambda p: (p.count("/"), len(p), p))[0], "prior: " + why
    imp = importers or collections.Counter()
    best = sorted(paths, key=lambda p: (bool(SNAPSHOT.search(p)), -imp[p], not p.startswith("realai/"),
                                        p.count("/"), len(p), p))[0]
    return best, ("heuristic: most imported (%d importers)" % imp[best]) if imp[best] else \
        "heuristic: no prior decision and no importers; non-snapshot, realai package, shallowest"


def build(root: Path = ROOT) -> Dict:
    groups = duplicate_groups(root)
    unresolved = [p for v in groups.values() for p in v]
    imp = _importers(root, unresolved)
    out = []
    for h, paths in sorted(groups.items(), key=lambda kv: kv[1][0]):
        canon, why = choose(paths, imp)
        out.append({"sha256": h, "canonical": canon, "why": why, "duplicates": [p for p in paths if p != canon]})
    return {"generated_by": "python -m realai.repo_hygiene.canonical_paths --write",
            "rule": "identical bytes, >= %d B, not __init__.py, tracked, outside shelves/tests" % MIN_BYTES,
            "archive_root_for_future_moves": "D:\\ARCHIVE",
            "moves_done": False, "groups": out}


def render_md(data: Dict) -> str:
    by_rule = collections.Counter(g["why"].split(":")[0] for g in data["groups"])
    lines = ["# Canonical paths (duplicated modules)", "",
             "Generated by `python -m realai.repo_hygiene.canonical_paths --write`; machine-readable copy: "
             "`config/canonical_paths.json`. **Nothing has been moved.** This is the contract for any later park.", "",
             "## Rules (agree with prior cleanup)", "",
             "Sources: `docs/AUTHORITY.md`, `docs/MONOREPO_TARGET_LAYOUT.md`, `scan_results/ONE_TREE.md`, "
             "`docs/NESTED_REALAI_PARK_AUDIT.md`, `_quarantine/twins_20260926/PHASE3_PARK.md`.", "",
             "| Priority | Prefix wins | Why |", "|---|---|---|"]
    for i, (p, why) in enumerate(PRIOR_RULES, 1):
        lines.append(f"| {i} | `{p}` | {why} |")
    lines += ["", "`abilities/rackup/` copies lose to `realai/plugins/` (rackup gold). Dest-empty shims (small re-export "
              "files) are not duplicates: they differ in bytes and stay, per MONOREPO_TARGET_LAYOUT.",
              "If no rule matches: the copy most imported by tracked code wins, then the `realai` package, then the "
              "shallowest path.", "",
              "## Moves policy", "",
              "- Approved so far: documentation and the duplicate guard test only. No parks in this change.",
              "- Any file later moved **out of `C:\\RealAI-clean`** goes to `D:\\ARCHIVE` (dated subfolder, same relative "
              "path). In-repo parks keep the existing `_quarantine/twins_<date>/` convention with a PARK note, "
              "grep-first, `git mv` so rollback is `git mv` back.",
              "- Never park: hive/bridge gold, `realai/abilities/__init__.py` shim, console/voice trainer UI, "
              "`realai/ability_catalog.py`.", "",
              "## Guard", "",
              "`tests/test_canonical_paths.py` fails when a new byte-identical importable duplicate appears, or a "
              "listed group gains a member. Current groups are allow-listed. After an intentional change, rerun "
              "`--write` and commit the json.", "",
              f"## Groups ({len(data['groups'])}; " + ", ".join(f"{k}: {v}" for k, v in by_rule.items()) + ")", "",
              "| Canonical | Duplicates | Why |", "|---|---|---|"]
    for g in data["groups"]:
        lines.append(f"| `{g['canonical']}` | " + "<br>".join(f"`{d}`" for d in g["duplicates"]) + f" | {g['why']} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    data = build()
    if a.write:
        JSON_PATH.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
        DOC_PATH.write_text(render_md(data), encoding="utf-8")
    c = collections.Counter(g["why"].split(":")[0] for g in data["groups"])
    print(json.dumps({"groups": len(data["groups"]), "files": sum(1 + len(g["duplicates"]) for g in data["groups"]),
                      "by_rule": c}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
