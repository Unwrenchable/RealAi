"""HTTP helpers for learned packets — list / get / promote stub.

Mounted by the orchestrator as GET/POST /v1/learn/*. Keeps orch thin.
Never patches orchestration gold beyond the route mount.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from realai.learn.pipeline import default_product_root
from realai.learn.scaffold import plugin_id_for, plugin_package_name, scaffold_plugin


def _product() -> Path:
    return default_product_root()


def _catalog_root(product: Path | None = None) -> Path:
    return (product or _product()) / "realai" / "catalog" / "learned"


def _docs_root(product: Path | None = None) -> Path:
    return (product or _product()) / "docs" / "learning"


def _plugins_root(product: Path | None = None) -> Path:
    return (product or _product()) / "realai" / "plugins"


def _index_path(product: Path | None = None) -> Path:
    return _catalog_root(product) / "index.json"


def _load_index(product: Path | None = None) -> dict[str, Any]:
    path = _index_path(product)
    if not path.is_file():
        return {"schema": "realai.learn.index/v1", "slugs": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"schema": "realai.learn.index/v1", "slugs": {}}


def _load_packet(slug: str, product: Path | None = None) -> dict[str, Any] | None:
    product = product or _product()
    slug = (slug or "").strip()
    if not slug:
        return None
    catalog = _catalog_root(product) / slug / "packet.json"
    docs = _docs_root(product) / f"{slug}.json"
    for path in (catalog, docs):
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except (OSError, json.JSONDecodeError):
                continue
    # index pointer
    idx = _load_index(product)
    row = (idx.get("slugs") or {}).get(slug) if isinstance(idx.get("slugs"), dict) else None
    if isinstance(row, dict) and row.get("packet"):
        p = Path(str(row["packet"]))
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except (OSError, json.JSONDecodeError):
                return None
    return None


def _has_stub(slug: str, product: Path | None = None) -> bool:
    product = product or _product()
    package = plugin_package_name(slug)
    plugin_dir = _plugins_root(product) / package
    if not plugin_dir.is_dir():
        return False
    return (plugin_dir / "__init__.py").is_file() or (plugin_dir / ".learned.json").is_file()


def _summarize_packet(packet: dict[str, Any], *, slug: str, product: Path) -> dict[str, Any]:
    summary = packet.get("summary") if isinstance(packet.get("summary"), dict) else {}
    fps = packet.get("fingerprints") or []
    fp_count = len(fps) if isinstance(fps, list) else int(packet.get("fingerprint_count") or 0)
    file_count = int(summary.get("file_count") or fp_count or 0)
    package = plugin_package_name(slug)
    plugin_id = plugin_id_for(package)
    catalog = _catalog_root(product) / slug / "packet.json"
    docs = _docs_root(product) / f"{slug}.json"
    return {
        "slug": slug,
        "id": plugin_id,
        "package": package,
        "title": summary.get("title") or slug,
        "description": (str(summary.get("description") or ""))[:320],
        "file_count": file_count,
        "fingerprint_count": fp_count,
        "languages": summary.get("languages") or {},
        "frameworks": list(summary.get("frameworks") or [])[:12],
        "domain_keywords": list(summary.get("domain_keywords") or [])[:20],
        "proposed_abilities": [
            {"id": a.get("id"), "description": (a.get("description") or "")[:120]}
            for a in (packet.get("proposed_abilities") or [])[:12]
            if isinstance(a, dict)
        ],
        "docs_path": str(docs) if docs.is_file() else None,
        "packet_path": str(catalog) if catalog.is_file() else None,
        "has_stub": _has_stub(slug, product),
        "plugin_dir": str(_plugins_root(product) / package),
        "learned_at": packet.get("learned_at"),
        "source": {
            "kind": (packet.get("source") or {}).get("kind")
            if isinstance(packet.get("source"), dict)
            else None,
            "path": (packet.get("source") or {}).get("resolved_path")
            or (packet.get("source") or {}).get("path")
            if isinstance(packet.get("source"), dict)
            else None,
        },
    }


def list_packets() -> dict[str, Any]:
    product = _product()
    idx = _load_index(product)
    slugs_map = idx.get("slugs") if isinstance(idx.get("slugs"), dict) else {}
    # Also pick up folder packets not yet in index
    catalog = _catalog_root(product)
    found: set[str] = set(str(k) for k in slugs_map.keys())
    if catalog.is_dir():
        for child in catalog.iterdir():
            if child.is_dir() and (child / "packet.json").is_file():
                found.add(child.name)

    rows: list[dict[str, Any]] = []
    for slug in sorted(found):
        packet = _load_packet(slug, product)
        if not packet:
            package = plugin_package_name(slug)
            rows.append(
                {
                    "slug": slug,
                    "id": plugin_id_for(package),
                    "file_count": 0,
                    "docs_path": str(_docs_root(product) / f"{slug}.json")
                    if (_docs_root(product) / f"{slug}.json").is_file()
                    else None,
                    "has_stub": _has_stub(slug, product),
                    "error": "packet_unreadable",
                }
            )
            continue
        rows.append(_summarize_packet(packet, slug=slug, product=product))

    return {
        "ok": True,
        "count": len(rows),
        "packets": rows,
        "index": str(_index_path(product)),
    }


def get_packet(slug: str) -> dict[str, Any]:
    product = _product()
    slug = (slug or "").strip()
    packet = _load_packet(slug, product)
    if not packet:
        return {"ok": False, "error": "not_found", "slug": slug}
    summary = _summarize_packet(packet, slug=slug, product=product)
    # Cap: never dump fingerprints
    return {"ok": True, "slug": slug, "packet": summary}


def promote_stub(slug: str, *, confirm: bool = False, mode: str = "stub") -> dict[str, Any]:
    """Write coach stub from an existing packet and refresh plugin registration."""
    if mode not in {"stub", "plugin", "scaffold"}:
        return {"ok": False, "error": f"unsupported_mode:{mode}", "hint": "use mode=stub"}
    if not confirm:
        return {
            "ok": False,
            "error": "confirm_required",
            "hint": 'POST {"slug":"...","mode":"stub","confirm":true}',
        }

    product = _product()
    slug = (slug or "").strip()
    packet = _load_packet(slug, product)
    if not packet:
        return {"ok": False, "error": "not_found", "slug": slug}

    plugins_root = _plugins_root(product)
    stub = scaffold_plugin(packet, plugins_root=plugins_root, write=True)
    package = str((stub.get("plugin_proposal") or {}).get("package") or plugin_package_name(slug))
    plugin_id = str((stub.get("plugin_proposal") or {}).get("id") or plugin_id_for(package))
    plugin_dir = plugins_root / package

    registered: dict[str, Any] | None = None
    register_error: str | None = None
    try:
        import importlib

        mod = importlib.import_module(f"realai.plugins.{package}")
        importlib.reload(mod)
        register = getattr(mod, "register", None)
        if callable(register):
            registered = register(None, {})
            if not isinstance(registered, dict):
                registered = {"ok": True, "name": package}
        else:
            registered = {"ok": True, "registered": False, "reason": "no register()"}
    except Exception as exc:
        register_error = str(exc)

    catalog_refresh: dict[str, Any] | None = None
    try:
        from realai.ability_catalog import build_catalog, coverage_summary, save_catalog

        cat = build_catalog()
        path = save_catalog(cat)
        catalog_refresh = {
            "ok": True,
            "path": str(path),
            "coverage": coverage_summary(),
            "ability_count": len(cat.get("abilities") or []),
        }
    except Exception as exc:
        catalog_refresh = {"ok": False, "error": str(exc)}

    return {
        "ok": bool(stub.get("wrote") or stub.get("ok")),
        "slug": slug,
        "mode": "stub",
        "plugin_id": plugin_id,
        "package": package,
        "plugin_path": str(plugin_dir),
        "plugin_dir": str(plugin_dir),
        "stub": {
            "wrote": bool(stub.get("wrote")),
            "upgraded": bool(stub.get("upgraded")),
            "abilities": stub.get("abilities") or [],
        },
        "registered": registered,
        "register_error": register_error,
        "catalog_refresh": catalog_refresh,
        "has_stub": plugin_dir.is_dir(),
    }


def dispatch_learn_get(path: str) -> dict[str, Any] | None:
    """Return a response dict for GET /v1/learn/... or None if not ours."""
    if path == "/v1/learn/packets":
        return list_packets()
    if path.startswith("/v1/learn/packets/"):
        slug = path[len("/v1/learn/packets/") :].strip("/")
        if not slug or "/" in slug:
            return {"ok": False, "error": "bad_slug"}
        return get_packet(slug)
    return None


def dispatch_learn_post(path: str, body: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return a response dict for POST /v1/learn/... or None if not ours."""
    if path == "/v1/learn/promote":
        body = body or {}
        return promote_stub(
            str(body.get("slug") or ""),
            confirm=bool(body.get("confirm")),
            mode=str(body.get("mode") or "stub"),
        )
    if path == "/v1/learn/queue":
        # Optional: packet-only queue (from scout). Never write unless body.write.
        from realai.learn.scout import handle_learn_queue_request

        return handle_learn_queue_request(body or {})
    return None
