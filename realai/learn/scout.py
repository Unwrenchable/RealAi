"""Learn scout — rank local workspaces + explicit URLs.

No whole-disk crawl. Only looks under explicit roots (env / product parent /
a few shallow known folders) and any paths/URLs the caller passes in.
Default learn is packet-only (write=False); plugin stubs still need --write.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence

from realai.learn.pipeline import default_product_root, run_learn
from realai.learn.source import infer_slug, slugify

# Markers that make a folder look like a learnable workspace (shallow only).
_REPO_MARKERS = (
    ".git",
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "README.md",
    "README.rst",
    "composer.json",
)

# Never scout into these directory names (even under an allowed root).
_SKIP_NAMES = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    "target",
    ".learn_cache",
    "recovery",
    "_quarantine",
}


def _packet_paths(product: Path, slug: str) -> tuple[Path, Path]:
    return (
        product / "realai" / "catalog" / "learned" / slug / "packet.json",
        product / "docs" / "learning" / f"{slug}.json",
    )


def packet_exists(slug: str, product: Path | None = None) -> bool:
    root = product or default_product_root()
    catalog, docs = _packet_paths(root, slug)
    return catalog.is_file() or docs.is_file()


def default_scout_roots(product: Path | None = None) -> List[Path]:
    """Allowed scout roots only — never the whole disk / whole user profile."""
    root = product or default_product_root()
    out: List[Path] = []
    seen: set[str] = set()

    def _add(p: Path) -> None:
        try:
            rp = p.expanduser().resolve()
        except OSError:
            return
        key = str(rp).lower()
        if key in seen:
            return
        if not rp.is_dir():
            return
        seen.add(key)
        out.append(rp)

    env = (os.environ.get("REALAI_LEARN_SCOUT_ROOTS") or "").strip()
    if env:
        for part in env.replace(",", ";").split(";"):
            part = part.strip().strip('"')
            if part:
                _add(Path(part))

    # Product tree itself + its parent (siblings like effective-engine-main)
    _add(root)
    _add(root.parent)

    # Shallow known folders under the user home — not a recursive home walk
    home = Path.home()
    for name in ("Projects", "repos", "src", "code", "dev", "work"):
        _add(home / name)

    return out


def _looks_like_workspace(path: Path) -> bool:
    if not path.is_dir():
        return False
    name = path.name.lower()
    if name in _SKIP_NAMES or name.startswith("."):
        return False
    for marker in _REPO_MARKERS:
        if (path / marker).exists():
            return True
    return False


def _score_workspace(path: Path, *, product: Path) -> dict[str, Any]:
    score = 0
    reasons: List[str] = []
    slug = infer_slug(str(path), path)

    if (path / ".git").exists():
        score += 40
        reasons.append("git")
    for marker, pts in (
        ("package.json", 15),
        ("pyproject.toml", 15),
        ("Cargo.toml", 10),
        ("go.mod", 10),
        ("README.md", 8),
        ("composer.json", 8),
    ):
        if (path / marker).exists():
            score += pts
            reasons.append(marker)

    # Prefer non-product foreign trees slightly for scout diversity
    try:
        if path.resolve() != product.resolve():
            score += 5
            reasons.append("foreign")
        else:
            score -= 10
            reasons.append("product_self")
    except OSError:
        pass

    already = packet_exists(slug, product)
    if already:
        score += 25
        reasons.append("packet_exists")

    return {
        "path": str(path),
        "slug": slug,
        "score": score,
        "reasons": reasons,
        "already_learned": already,
        "kind": "local",
    }


def _iter_shallow_candidates(root: Path, *, max_depth: int = 2) -> Iterable[Path]:
    """Depth-limited listing under one allowed root. No deep recursion."""
    root = root.resolve()
    if _looks_like_workspace(root):
        yield root

    try:
        level1 = sorted(
            [p for p in root.iterdir() if p.is_dir() and p.name.lower() not in _SKIP_NAMES],
            key=lambda p: p.name.lower(),
        )
    except OSError:
        return

    for child in level1:
        if _looks_like_workspace(child):
            yield child
        if max_depth < 2:
            continue
        # One more level for nests like effective-engine-main/effective-engine-main
        try:
            level2 = sorted(
                [p for p in child.iterdir() if p.is_dir() and p.name.lower() not in _SKIP_NAMES],
                key=lambda p: p.name.lower(),
            )
        except OSError:
            continue
        for grand in level2:
            if _looks_like_workspace(grand):
                yield grand


def scout(
    *,
    roots: Sequence[str | Path] | None = None,
    urls: Sequence[str] | None = None,
    paths: Sequence[str | Path] | None = None,
    product_root: Path | None = None,
    max_candidates: int = 20,
    max_depth: int = 2,
) -> dict[str, Any]:
    """Rank local workspaces under allowed roots + explicit paths/URLs.

    Explicit URLs are ranked but not fetched here (queue/run_learn clones).
    """
    product = Path(product_root) if product_root is not None else default_product_root()
    root_list: List[Path] = []
    if roots:
        for r in roots:
            try:
                rp = Path(r).expanduser().resolve()
            except OSError:
                continue
            if rp.is_dir():
                root_list.append(rp)
    else:
        root_list = default_scout_roots(product)

    ranked: dict[str, dict[str, Any]] = {}

    for root in root_list:
        for cand in _iter_shallow_candidates(root, max_depth=max_depth):
            try:
                key = str(cand.resolve()).lower()
            except OSError:
                continue
            if key in ranked:
                continue
            ranked[key] = _score_workspace(cand, product=product)

    # Explicit local paths always included
    for raw in paths or []:
        p = Path(str(raw)).expanduser()
        try:
            if p.is_dir():
                rp = p.resolve()
                ranked[str(rp).lower()] = _score_workspace(rp, product=product)
        except OSError:
            continue

    # Explicit URLs / owner/repo — no network here
    url_rows: List[dict[str, Any]] = []
    for u in urls or []:
        s = str(u or "").strip()
        if not s:
            continue
        slug = infer_slug(s)
        already = packet_exists(slug, product)
        url_rows.append(
            {
                "path": s,
                "slug": slug,
                "score": 50 + (25 if already else 0),
                "reasons": ["explicit_url"] + (["packet_exists"] if already else []),
                "already_learned": already,
                "kind": "remote",
            }
        )

    locals_sorted = sorted(ranked.values(), key=lambda r: (-int(r["score"]), r["slug"]))
    combined = locals_sorted + url_rows
    combined.sort(key=lambda r: (-int(r["score"]), r["slug"]))
    top = combined[: max(1, int(max_candidates))]

    return {
        "ok": True,
        "product_root": str(product),
        "roots": [str(r) for r in root_list],
        "count": len(top),
        "candidates": top,
        "write_default": False,
        "note": "packet only unless --write; no whole-disk crawl",
    }


def run_learn_queue(
    sources: Sequence[str],
    *,
    write: bool = False,
    refresh: bool = False,
    noop_if_packet: bool = True,
    all_branches: bool = False,
    max_files: int = 800,
    max_branches: int = 40,
    product_root: Path | None = None,
) -> dict[str, Any]:
    """Run run_learn(write=False by default) over an explicit queue.

    When noop_if_packet and a packet already exists (and not refresh), skip
    the scan and report the existing paths.
    """
    product = Path(product_root) if product_root is not None else default_product_root()
    results: List[dict[str, Any]] = []

    for raw in sources:
        src = str(raw or "").strip()
        if not src:
            continue
        # Local path slug preview
        p = Path(src).expanduser()
        slug = infer_slug(src, p if p.exists() else None)
        catalog, docs = _packet_paths(product, slug)

        if noop_if_packet and not refresh and (catalog.is_file() or docs.is_file()):
            results.append(
                {
                    "ok": True,
                    "action": "noop",
                    "slug": slug,
                    "source": src,
                    "packet_path": str(catalog) if catalog.is_file() else None,
                    "docs_path": str(docs) if docs.is_file() else None,
                    "wrote_plugin": False,
                    "heal": False,
                }
            )
            continue

        learned = run_learn(
            src,
            write=bool(write),
            refresh=bool(refresh),
            all_branches=bool(all_branches),
            max_files=int(max_files),
            max_branches=int(max_branches),
            product_root=product,
        )
        learned = dict(learned)
        learned["action"] = "refresh" if (catalog.is_file() or docs.is_file()) else "learn"
        results.append(learned)

    ok = all(bool(r.get("ok")) for r in results) if results else True
    return {
        "ok": ok,
        "heal": False,
        "write": bool(write),
        "count": len(results),
        "results": results,
    }


def scout_and_queue(
    *,
    paths: Sequence[str | Path] | None = None,
    urls: Sequence[str] | None = None,
    roots: Sequence[str | Path] | None = None,
    write: bool = False,
    refresh: bool = False,
    noop_if_packet: bool = True,
    max_candidates: int = 8,
    all_branches: bool = False,
    max_files: int = 800,
    product_root: Path | None = None,
) -> dict[str, Any]:
    """Scout then learn-queue top candidates (packet-only unless write=True)."""
    if write:
        # Hard rule this pass: scout/auto defaults packet-only; caller must
        # opt into stubs explicitly and we still allow it when requested.
        pass
    report = scout(
        roots=roots,
        urls=urls,
        paths=paths,
        product_root=product_root,
        max_candidates=max_candidates,
    )
    # Explicit paths/URLs: queue only those (scout report still returned).
    # Bare /learn auto: queue top scout candidates.
    explicit = [str(x) for x in list(paths or []) + list(urls or []) if str(x).strip()]
    if explicit:
        sources = explicit
    else:
        sources = [str(c.get("path")) for c in report.get("candidates") or [] if c.get("path")]
    queued = run_learn_queue(
        sources,
        write=bool(write),
        refresh=bool(refresh),
        noop_if_packet=bool(noop_if_packet) and not write,
        all_branches=bool(all_branches),
        max_files=int(max_files),
        product_root=product_root,
    )
    return {
        "ok": bool(report.get("ok")) and bool(queued.get("ok")),
        "heal": False,
        "scout": report,
        "queue": queued,
        "wrote_plugin": bool(write),
    }


def handle_learn_queue_request(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Body handler for an optional POST /v1/learn/queue (packet-only).

    Mount from the orchestrator when desired — this module stays free of orch
    imports so Craft can call it without touching gold orchestration.
    """
    body = body or {}
    write = bool(body.get("write"))
    # Force packet-only unless explicitly write=true
    sources = body.get("sources") or body.get("queue") or []
    if isinstance(sources, str):
        sources = [sources]
    paths = body.get("paths") or []
    urls = body.get("urls") or []
    auto = bool(body.get("auto"))

    if auto or (not sources and not paths and not urls):
        return scout_and_queue(
            paths=list(paths) if paths else None,
            urls=list(urls) if urls else None,
            write=write,
            refresh=bool(body.get("refresh")),
            noop_if_packet=not bool(body.get("refresh")),
            max_candidates=int(body.get("max_candidates") or 8),
            all_branches=bool(body.get("all_branches", False)),
            max_files=int(body.get("max_files") or 800),
        )

    merged = [str(s) for s in list(sources) + list(paths) + list(urls) if str(s).strip()]
    return run_learn_queue(
        merged,
        write=write,
        refresh=bool(body.get("refresh")),
        noop_if_packet=not bool(body.get("refresh")),
        all_branches=bool(body.get("all_branches", False)),
        max_files=int(body.get("max_files") or 800),
    )
