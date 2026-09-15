"""Git-learn pipeline — scan, packet, optional plugin stub. Never starts heal."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from realai.learn.packet import build_packet, validate_packet, write_packet
from realai.learn.scaffold import plugin_id_for, plugin_package_name, scaffold_plugin
from realai.learn.scan import DEFAULT_MAX_BRANCHES, FINGERPRINT_CAP, scan_source
from realai.learn.signals import extract_signals
from realai.learn.source import infer_slug, resolve_source

_PKG = Path(__file__).resolve().parent
_PRODUCT = _PKG.parent.parent  # repo root (parent of realai/)


def default_product_root() -> Path:
    env = (os.environ.get("REALAI_LEARN_ROOT") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    try:
        from realai.workspace import product_root

        return product_root()
    except Exception:
        return _PRODUCT


def default_cache_dir(product: Path | None = None) -> Path:
    root = product or default_product_root()
    return root / "realai" / ".learn_cache"


def run_learn(
    source: str = ".",
    *,
    write: bool = False,
    refresh: bool = False,
    product_root: Path | None = None,
    cache_dir: Path | None = None,
    plugins_root: Path | None = None,
    packet_root: Path | None = None,
    docs_root: Path | None = None,
    max_files: int = FINGERPRINT_CAP,
    max_branches: int = DEFAULT_MAX_BRANCHES,
    all_branches: bool = True,
) -> dict[str, Any]:
    """Scan a git source, emit a learning packet, optionally scaffold a plugin stub.

    Never starts heal, GPU, or the orchestrator.
    """
    product = Path(product_root) if product_root is not None else default_product_root()
    cache = Path(cache_dir) if cache_dir is not None else default_cache_dir(product)
    plugins = Path(plugins_root) if plugins_root is not None else product / "realai" / "plugins"
    catalog_root = (
        Path(packet_root) if packet_root is not None else product / "realai" / "catalog" / "learned"
    )
    docs = Path(docs_root) if docs_root is not None else product / "docs" / "learning"

    resolved = resolve_source(source, cache_dir=cache, refresh=refresh)
    if not resolved.get("ok"):
        return {
            "ok": False,
            "heal": False,
            "error": resolved.get("error") or "resolve_failed",
            "hint": resolved.get("hint"),
            "source": resolved,
        }

    tree = Path(resolved["path"])
    slug = str(resolved.get("slug") or infer_slug(source, tree))
    scan = scan_source(
        tree,
        all_branches=bool(all_branches),
        max_files=int(max_files),
        max_branches=int(max_branches),
    )
    signals = extract_signals(tree, list(scan.get("fingerprints") or []))
    package = plugin_package_name(slug)
    plugin_id = plugin_id_for(package)
    plugin_proposal = {
        "id": plugin_id,
        "package": package,
        "path": str(plugins / package),
        "http": {
            "canonical": f"/v1/plugins/{plugin_id}",
            "alias": f"/v1/learned/{package}",
        },
    }
    packet = build_packet(
        slug=slug,
        source=resolved,
        scan=scan,
        signals=signals,
        plugin_proposal=plugin_proposal,
    )
    shape_errors = validate_packet(packet)
    catalog_path = catalog_root / slug / "packet.json"
    docs_path = docs / f"{slug}.json"
    written = write_packet(packet, catalog_path=catalog_path, docs_path=docs_path)

    index_path = catalog_root / "index.json"
    _update_index(index_path, slug=slug, packet_path=catalog_path, plugin_id=plugin_id)

    stub: dict[str, Any] | None = None
    if write:
        stub = scaffold_plugin(packet, plugins_root=plugins, write=True)
        if stub.get("plugin_proposal"):
            packet["plugin_proposal"] = stub["plugin_proposal"]
            write_packet(packet, catalog_path=catalog_path, docs_path=docs_path)
    else:
        stub = scaffold_plugin(packet, plugins_root=plugins, write=False)

    return {
        "ok": not shape_errors,
        "heal": False,
        "slug": slug,
        "source": {
            "input": resolved.get("input"),
            "kind": resolved.get("kind"),
            "path": str(tree),
            "url": resolved.get("url"),
            "cloned": bool(resolved.get("cloned")),
            "reused_cache": bool(resolved.get("reused_cache")),
            "git": resolved.get("git") or {},
        },
        "packet_path": written.get("catalog"),
        "docs_path": written.get("docs"),
        "packet": packet,
        "shape_errors": shape_errors,
        "stub": stub,
        "wrote_plugin": bool(write and stub and stub.get("wrote")),
        "scan": {
            "all_branches": bool(all_branches),
            "max_files": int(max_files),
            "max_branches": int(max_branches),
            "file_count": int(scan.get("file_count") or 0),
            "truncated": bool(scan.get("truncated")),
            "branches_seen": list(scan.get("branches_seen") or []),
            "branch_counts": dict(scan.get("branch_counts") or {}),
            "branches_truncated": bool(scan.get("branches_truncated")),
        },
    }


def _update_index(index_path: Path, *, slug: str, packet_path: Path, plugin_id: str) -> None:
    data: dict[str, Any] = {"schema": "realai.learn.index/v1", "slugs": {}}
    if index_path.is_file():
        try:
            loaded = json.loads(index_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, json.JSONDecodeError):
            pass
    slugs = data.setdefault("slugs", {})
    if not isinstance(slugs, dict):
        slugs = {}
        data["slugs"] = slugs
    slugs[slug] = {
        "packet": str(packet_path),
        "plugin_id": plugin_id,
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
