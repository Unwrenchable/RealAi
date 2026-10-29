"""Regenerate docs/spine/orchestrators.csv (Phase 1a). Read-only: parses with ast, never imports.

Run from the repo root:  python docs/spine/build_orchestrators_csv.py
An "orchestrator copy" is any git-tracked .py whose filename contains "orchestrat".
"""
import ast, csv, hashlib, re, subprocess, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = "realai/orchestration/v3_orchestrator.py"


def tracked_py():
    out = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [p for p in out.splitlines() if (ROOT / p).is_file()]


def modname(path):
    p = path[:-3].replace("/", ".")
    return p[: -len(".__init__")] if p.endswith(".__init__") else p


def parse(path):
    try:
        return ast.parse((ROOT / path).read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return None


def imports_of(path, tree):
    """Yield (absolute_module, is_star)."""
    pkg = modname(path).split(".")
    if not path.endswith("__init__.py"):
        pkg = pkg[:-1]
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                yield a.name, False
        elif isinstance(n, ast.ImportFrom):
            if n.level:
                base = pkg[: len(pkg) - (n.level - 1)] if n.level > 1 else pkg
                mod = ".".join(base + ([n.module] if n.module else []))
            else:
                mod = n.module or ""
            star = any(a.name == "*" for a in n.names)
            yield mod, star
            for a in n.names:
                if a.name != "*":
                    yield f"{mod}.{a.name}", False


PATH_RE = re.compile(r"(sys\.path\.(insert|append)|importlib\.util\.spec_from_file_location|runpy\.run_path|__import__\()")


def main():
    files = tracked_py()
    targets = [p for p in files if "orchestrat" in Path(p).name.lower()]
    tmod = {modname(p): p for p in targets}
    importers = defaultdict(set)
    style = {}
    for f in files:
        tree = parse(f)
        if tree is None:
            continue
        for mod, star in imports_of(f, tree):
            if mod in tmod and tmod[mod] != f:
                importers[tmod[mod]].add(f)
    hashes = {}
    for t in targets:
        data = (ROOT / t).read_bytes()
        hashes[t] = (hashlib.sha256(data).hexdigest(), len(data))
        tree = parse(t)
        src = data.decode("utf-8", "replace")
        kinds = []
        if tree is not None and any(isinstance(n, ast.ImportFrom) and any(a.name == "*" for a in n.names) for n in tree.body):
            kinds.append("import *")
        if PATH_RE.search(src):
            kinds.append("path-based")
        style[t] = "+".join(kinds) or ("normal" if tree is not None else "syntax-error")
    first_by_hash = {}
    for t in sorted(targets, key=lambda p: (p.count("/"), p)):
        first_by_hash.setdefault(hashes[t][0], t)
    rows = []
    for t in sorted(targets):
        sha, size = hashes[t]
        imp = sorted(importers[t])
        if t == CORE:
            fate = "core"
        elif first_by_hash[sha] != t:
            fate = "archive" if not imp else "shim"
        elif t.startswith(("abilities/", "realai/abilities/", "modules/")) and imp:
            fate = "plugin"
        elif imp:
            fate = "shim"
        else:
            fate = "archive"
        dup = "" if first_by_hash[sha] == t else first_by_hash[sha]
        rows.append([t, sha, size, len(imp), "; ".join(imp[:3]), style[t], fate, dup])
    out = ROOT / "docs/spine/orchestrators.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["path", "sha256", "size", "imported_by_count", "imported_by_examples", "import_style", "proposed_fate", "duplicate_of"])
        w.writerows(rows)
    print(f"{len(rows)} orchestrator copies -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
