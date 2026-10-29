"""Phase 1b (ONE_SPINE_PLAN section 1): no production module imports an archive-verdict file.

Archive-verdict files come from docs/spine/orchestrators.csv (proposed_fate == "archive").
Static only (ast; nothing is imported or executed). An edge is counted when a production
.py (anything tracked except tests/, docs/spine/ and the archive-verdict files themselves)
  * statically imports the module (``import m`` / ``from m import x`` / ``from pkg import m``), or
  * names it in a string literal used for dynamic/path-based loading: the exact dotted name
    (``importlib.import_module("realai.x")``, routing tables) or its repo path ("a/b.py").
    Docstrings are ignored.

KNOWN_DYNAMIC lists edges that already exist on main. Each must be rewired (or the file's
verdict changed) BEFORE the batch that archives its target; the test fails on any NEW edge,
and also when a KNOWN edge disappears, so the list can only shrink deliberately.
"""
import ast, csv, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_import_graph as g  # noqa: E402  (shared static walker)

CSV = g.ROOT / "docs" / "spine" / "orchestrators.csv"

KNOWN_DYNAMIC = {
    # orchestrator surface catalogue + importlib.import_module dispatch
    "abilities/orchestration_surface.py -> realai/orchestration/legacy_orchestrator.py",
}


def _archive():
    with CSV.open(encoding="utf-8", newline="") as fh:
        return {r["path"] for r in csv.DictReader(fh) if r["proposed_fate"] == "archive"}


def _docstring_ids(tree):
    ids = set()
    for n in ast.walk(tree):
        body = getattr(n, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            ids.add(id(body[0].value))
    return ids


def archive_edges():
    arch = _archive()
    by_mod = {g._modname(p): p for p in arch}
    files = g._tracked_py()
    prod = [f for f in files if f not in arch and not f.startswith(("tests/", "docs/spine/"))]
    prod_set = set(prod)
    edges = set()
    for f, m in g._edges(prod):
        if f not in prod_set:
            continue
        for cand in (m, m.rsplit(".", 1)[0]):
            if cand in by_mod:
                edges.add(f"{f} -> {by_mod[cand]}")
    paths = {p: p for p in arch} | {p.replace("/", "\\"): p for p in arch}
    for f in prod:
        try:
            tree = ast.parse((g.ROOT / f).read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, ValueError):
            continue
        skip = _docstring_ids(tree)
        for n in ast.walk(tree):
            if not (isinstance(n, ast.Constant) and isinstance(n.value, str)) or id(n) in skip:
                continue
            s = n.value.strip()
            if s in by_mod:
                edges.add(f"{f} -> {by_mod[s]}")
                continue
            for k, p in paths.items():
                if k in s:
                    edges.add(f"{f} -> {p}")
    return edges


def test_archive_targets_listed():
    arch = _archive()
    assert len(arch) > 0
    missing = sorted(p for p in arch if not (g.ROOT / p).is_file())
    assert not missing, f"archive-verdict paths missing from tree: {missing}"


def test_no_production_import_of_archive_files():
    edges = archive_edges()
    new = sorted(edges - KNOWN_DYNAMIC)
    assert not new, "Production code imports archive-verdict files (rewire or keep a shim):\n" + "\n".join(new)
    gone = sorted(KNOWN_DYNAMIC - edges)
    assert not gone, "KNOWN_DYNAMIC entries no longer present; remove them:\n" + "\n".join(gone)


def test_known_edges_block_their_targets():
    """Archive batch helper: files still referenced by KNOWN_DYNAMIC are not archivable yet."""
    blocked = sorted({e.split(" -> ")[1] for e in KNOWN_DYNAMIC})
    assert all(p in _archive() for p in blocked), blocked
