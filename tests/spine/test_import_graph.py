"""Phase 1a/1b skeleton: static import graph (ast only, nothing is imported or executed).

Asserts every *repo-local* module imported somewhere still resolves to an existing file
or package directory. Imports that already fail to resolve on main are frozen in
tests/spine/import_graph_baseline.txt, so this passes today and fails on any NEW break
(e.g. an archive batch that removes a file someone still imports).
Regenerate the baseline (only when intentionally shrinking it):
    REALAI_SPINE_WRITE_BASELINE=1 python -m pytest tests/spine/test_import_graph.py
"""
import ast, os, subprocess, warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BASELINE = Path(__file__).with_name("import_graph_baseline.txt")


def _tracked_py():
    try:
        out = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except Exception:
        pytest.skip("git not available")
    return [p for p in out.splitlines() if (ROOT / p).is_file()]


def _modname(path):
    p = path[:-3].replace("/", ".")
    return p[: -len(".__init__")] if p.endswith(".__init__") else p


def _exists(mod):
    rel = ROOT.joinpath(*mod.split("."))
    return rel.with_suffix(".py").is_file() or rel.is_dir() or rel.with_suffix(".pyi").is_file()


def _edges(files):
    top = {p.split("/")[0] for p in files if "/" in p} | {Path(p).stem for p in files if "/" not in p}
    for f in files:
        try:
            tree = ast.parse((ROOT / f).read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, ValueError):
            continue
        pkg = _modname(f).split(".")
        if not f.endswith("__init__.py"):
            pkg = pkg[:-1]
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom):
                if n.level:
                    base = pkg[: len(pkg) - (n.level - 1)] if n.level > 1 else pkg
                    mod = ".".join(base + ([n.module] if n.module else []))
                else:
                    mod = n.module or ""
                if not mod:
                    continue
                mods = [mod]
            else:
                continue
            for m in mods:
                if m.split(".")[0] in top or (isinstance(n, ast.ImportFrom) and n.level):
                    yield f, m


def _unresolved():
    bad = set()
    for f, m in _edges(_tracked_py()):
        if not _exists(m):
            bad.add(f"{f} -> {m}")
    return bad


def test_repo_local_imports_resolve():
    bad = _unresolved()
    if os.environ.get("REALAI_SPINE_WRITE_BASELINE"):
        BASELINE.write_text("\n".join(sorted(bad)) + "\n", encoding="utf-8")
    known = {l.strip() for l in BASELINE.read_text(encoding="utf-8").splitlines() if l.strip()} if BASELINE.exists() else set()
    new = sorted(bad - known)
    assert not new, "New unresolved repo-local imports (fix importers or keep a shim):\n" + "\n".join(new[:50])
    stale = sorted(known - bad)
    if stale:
        warnings.warn(f"{len(stale)} stale baseline entries now resolve (shrink baseline): " + "; ".join(stale[:20]))
