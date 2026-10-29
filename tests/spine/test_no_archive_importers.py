"""Phase 1b (ONE_SPINE_PLAN section 1): no production module imports an archive-verdict file.

Archive-verdict files come from docs/spine/orchestrators.csv (proposed_fate == "archive").
Static only (ast; nothing is imported or executed). An edge is counted when a production
.py (anything tracked except tests/, docs/spine/ and the archive-verdict files themselves)
  * statically imports the module (``import m`` / ``from m import x`` / ``from pkg import m``), or
  * names it in a string literal used for dynamic/path-based loading: the exact dotted name
    (``importlib.import_module("realai.x")``, routing tables) or its repo path ("a/b.py").
    Docstrings are ignored.
For ``from base import name`` (absolute or relative) BOTH ``base`` and ``base.name`` are checked,
so ``from realai.orchestration import legacy_orchestrator`` and ``from .orchestration import x``
(relative bases resolved from the importing file's package and ``level``) are caught.

Static limits (NOT detected; review by hand):
  * ``importlib.import_module(".x", package="pkg")`` / ``import_module(name, package=...)``
    (relative name + package arg is not resolved),
  * names built by string concatenation, ``%``/``.format`` or f-strings,
  * paths built with ``os.path.join`` / ``Path`` ``/`` segments (e.g. ``_ROOT / "realai" / "x.py"``),
  * aliased package roots on sys.path (e.g. ``core.x`` meaning ``realai/core/x.py``).
Known instances of these are pinned in KNOWN_PATH_PROBES and checked by literal presence.

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
    "abilities/orchestration_surface.py -> realai/orchestration/realai_orchestrator.py",
    "abilities/orchestration_surface.py -> realai/orchestration/legacy_orchestrator.py",
    "abilities/orchestration_surface.py -> realai/orchestration/unified_orchestrator.py",
    # hive routing tables ("domain"/"hive" -> abilities.hive_orchestrator)
    "realai/core_hive_router.py -> abilities/hive_orchestrator.py",
    "realai/orchestration/v3_runtime_bridge.py -> abilities/hive_orchestrator.py",
}

# Probes the static walker cannot see (see "Static limits"). Same "src -> target" format.
# Each entry maps to a literal snippet that must still be present in src; the test fails when
# the snippet disappears so the list can only shrink deliberately.
KNOWN_PATH_PROBES = {
    # core surface catalogue: "module": "core.orchestrator" / "path": "orchestrator.py" (realai/core alias)
    "abilities/core_surface.py -> realai/core/orchestrator.py": '"module": "core.orchestrator"',
    # related-path probe built with _ROOT / "realai" / "orchestrator.py"
    "abilities/orchestration_surface.py -> realai/orchestrator.py": '_ROOT / "realai" / "orchestrator.py"',
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


def _pkg(f):
    pkg = g._modname(f).split(".")
    return pkg if f.endswith("__init__.py") else pkg[:-1]


def _static_mods(f, tree):
    """Dotted candidates for every import in tree, incl. base.alias for ImportFrom."""
    pkg = _pkg(f)
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                yield a.name
        elif isinstance(n, ast.ImportFrom):
            if n.level:
                base = pkg[: len(pkg) - (n.level - 1)] if n.level > 1 else list(pkg)
                mod = ".".join(base + ([n.module] if n.module else []))
            else:
                mod = n.module or ""
            if mod:
                yield mod
            for a in n.names:
                if a.name != "*":
                    yield f"{mod}.{a.name}" if mod else a.name


def edges_in_source(f, src, by_mod):
    tree = ast.parse(src)
    out = set()
    for m in _static_mods(f, tree):
        if m in by_mod:
            out.add(f"{f} -> {by_mod[m]}")
    return out


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
    for f in prod:
        try:
            edges |= edges_in_source(f, (g.ROOT / f).read_text(encoding="utf-8", errors="replace"), by_mod)
        except (SyntaxError, ValueError):
            continue
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
    blocked = sorted({e.split(" -> ")[1] for e in KNOWN_DYNAMIC | set(KNOWN_PATH_PROBES)})
    assert all(p in _archive() for p in blocked), blocked


def test_known_path_probes_present():
    gone = []
    for edge, snippet in KNOWN_PATH_PROBES.items():
        src = edge.split(" -> ")[0]
        if snippet not in (g.ROOT / src).read_text(encoding="utf-8", errors="replace"):
            gone.append(edge)
    assert not gone, "KNOWN_PATH_PROBES entries no longer present; remove them:\n" + "\n".join(gone)


_BY_MOD = {"realai.orchestration.legacy_orchestrator": "realai/orchestration/legacy_orchestrator.py"}


def test_mutation_absolute_from_import_of_submodule():
    src = "from realai.orchestration import legacy_orchestrator\n"
    assert edges_in_source("abilities/x.py", src, _BY_MOD) == {
        "abilities/x.py -> realai/orchestration/legacy_orchestrator.py"}


def test_mutation_relative_from_import():
    f = "realai/fake_mod.py"  # package realai
    for src in ("from .orchestration import legacy_orchestrator\n",
                "from .orchestration.legacy_orchestrator import X\n"):
        assert edges_in_source(f, src, _BY_MOD) == {
            f"{f} -> realai/orchestration/legacy_orchestrator.py"}, src
    f2 = "realai/orchestration/sub/y.py"  # level 2 -> realai.orchestration
    assert edges_in_source(f2, "from .. import legacy_orchestrator\n", _BY_MOD) == {
        f"{f2} -> realai/orchestration/legacy_orchestrator.py"}
