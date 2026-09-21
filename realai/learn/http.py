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
        "scores": list(packet.get("scores") or [])[:40],
        "score_top": list(packet.get("scores") or [])[:8],
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




def _wired_registry_path(product: Path | None = None) -> Path:
    return _catalog_root(product) / "wired_abilities.json"


def _load_wired(product: Path | None = None) -> list[dict]:
    path = _wired_registry_path(product)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data.get("abilities") if isinstance(data, dict) else data
        return list(rows) if isinstance(rows, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _save_wired(rows: list[dict], product: Path | None = None) -> Path:
    product = product or _product()
    path = _wired_registry_path(product)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema": "realai.learn.wired/v1", "abilities": rows}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return path


def wire_learned(
    slug: str,
    *,
    target: str = "ability",
    ability_id: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Wire a learned module into abilities/ or plugin registry — never copy foreign code."""
    if not confirm:
        return {
            "ok": False,
            "error": "confirm_required",
            "hint": 'POST {"slug":"...","target":"ability|plugin","confirm":true}',
        }
    target = (target or "ability").strip().lower()
    if target not in {"ability", "plugin"}:
        return {"ok": False, "error": f"bad_target:{target}"}

    product = _product()
    slug = (slug or "").strip()
    packet = _load_packet(slug, product)
    if not packet:
        return {"ok": False, "error": "not_found", "slug": slug}

    package = plugin_package_name(slug)
    plugin_id = plugin_id_for(package)
    plugin_dir = _plugins_root(product) / package
    if not plugin_dir.is_dir():
        # auto-scaffold stub first (packet only module)
        stub = scaffold_plugin(packet, plugins_root=_plugins_root(product), write=True)
        if not (stub.get("wrote") or plugin_dir.is_dir()):
            return {
                "ok": False,
                "error": "stub_missing",
                "hint": "POST /v1/learn/promote first",
                "stub": stub,
            }

    if target == "plugin":
        registered = None
        reg_err = None
        try:
            import importlib

            mod = importlib.import_module(f"realai.plugins.{package}")
            importlib.reload(mod)
            register = getattr(mod, "register", None)
            if callable(register):
                registered = register(None, {})
            # Ensure package appears in a lightweight registry index
            reg_path = _plugins_root(product) / "registry.json"
            reg = {"plugins": []}
            if reg_path.is_file():
                try:
                    reg = json.loads(reg_path.read_text(encoding="utf-8")) or reg
                except (OSError, json.JSONDecodeError):
                    pass
            plugs = reg.setdefault("plugins", [])
            if not isinstance(plugs, list):
                plugs = []
                reg["plugins"] = plugs
            if not any(isinstance(x, dict) and x.get("package") == package for x in plugs):
                plugs.append(
                    {
                        "package": package,
                        "id": plugin_id,
                        "slug": slug,
                        "learned": True,
                        "path": str(plugin_dir),
                    }
                )
            reg_path.write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")
        except Exception as exc:
            reg_err = str(exc)
        catalog_refresh = None
        try:
            from realai.ability_catalog import build_catalog, coverage_summary, save_catalog

            cat = build_catalog()
            catalog_refresh = {
                "ok": True,
                "path": str(save_catalog(cat)),
                "coverage": coverage_summary(),
            }
        except Exception as exc:
            catalog_refresh = {"ok": False, "error": str(exc)}
        return {
            "ok": reg_err is None,
            "slug": slug,
            "target": "plugin",
            "plugin_id": plugin_id,
            "package": package,
            "plugin_path": str(plugin_dir),
            "registered": registered,
            "register_error": reg_err,
            "catalog_refresh": catalog_refresh,
        }

    # ability wire
    scores = list(packet.get("scores") or [])
    top = next((s for s in scores if s.get("kind") in {"ability", "plugin", "tool"}), None)
    aid = (ability_id or "").strip()
    if not aid:
        if top and top.get("path"):
            stem = Path(str(top["path"])).stem
            aid = plugin_package_name(slug).replace("_learned", "") + "_" + stem
        else:
            aid = package.replace("_learned", "") + "_bridge"
    aid = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in aid.lower()).strip("_") or "learned_bridge"

    abilities_dir = product / "abilities"
    abilities_dir.mkdir(parents=True, exist_ok=True)
    ability_path = abilities_dir / f"{aid}.py"
    body = f'''"""Learned ability bridge for `{slug}` — wraps plugins.{package}.invoke.

Generated by POST /v1/learn/wire. Never copies foreign source.
Status: PARTIAL (learned).
"""
from __future__ import annotations

from typing import Any


def run(payload: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {{}}
    context = context or {{}}
    try:
        from realai.plugins.{package} import invoke
    except Exception as exc:
        return {{"ok": False, "error": f"import_failed: {{exc}}", "learned": True, "status": "PARTIAL"}}
    data = dict(payload)
    data.setdefault("ability", "{aid}")
    data.setdefault("input", payload.get("input") or payload.get("task") or "")
    try:
        out = invoke(data)
    except Exception as exc:
        return {{"ok": False, "error": str(exc), "learned": True, "status": "PARTIAL"}}
    if isinstance(out, dict):
        out.setdefault("learned", True)
        out.setdefault("status", "PARTIAL")
        out.setdefault("wired_from", "{slug}")
        return out
    return {{"ok": True, "result": out, "learned": True, "status": "PARTIAL", "wired_from": "{slug}"}}


# Alias used by some ability loaders
def execute(payload: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
    return run(payload, context)
'''
    ability_path.write_text(body, encoding="utf-8")

    rows = _load_wired(product)
    rows = [r for r in rows if not (isinstance(r, dict) and r.get("id") == aid)]
    rows.append(
        {
            "id": aid,
            "name": aid,
            "status": "PARTIAL",
            "learned": True,
            "slug": slug,
            "package": package,
            "plugin_id": plugin_id,
            "modules": [f"abilities/{aid}.py", f"realai/plugins/{package}"],
            "live_path": f"POST /v1/tools/execute ability.{aid} (learned bridge)",
            "keywords": [slug, package, "learned", "wire"],
        }
    )
    reg_path = _save_wired(rows, product)

    catalog_refresh = None
    try:
        from realai.ability_catalog import build_catalog, coverage_summary, save_catalog

        cat = build_catalog()
        catalog_refresh = {
            "ok": True,
            "path": str(save_catalog(cat)),
            "coverage": coverage_summary(),
            "ability_count": len(cat.get("abilities") or []),
        }
    except Exception as exc:
        catalog_refresh = {"ok": False, "error": str(exc)}

    return {
        "ok": True,
        "slug": slug,
        "target": "ability",
        "ability_id": aid,
        "ability_path": str(ability_path),
        "status": "PARTIAL",
        "package": package,
        "plugin_id": plugin_id,
        "wired_registry": str(reg_path),
        "catalog_refresh": catalog_refresh,
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
    body = body or {}
    if path == "/v1/learn/promote":
        return promote_stub(
            str(body.get("slug") or ""),
            confirm=bool(body.get("confirm")),
            mode=str(body.get("mode") or "stub"),
        )
    if path == "/v1/learn/wire":
        return wire_learned(
            str(body.get("slug") or ""),
            target=str(body.get("target") or "ability"),
            ability_id=(str(body.get("id") or body.get("ability_id") or "").strip() or None),
            confirm=bool(body.get("confirm")),
        )
    if path == "/v1/learn/queue":
        from realai.learn.scout import handle_learn_queue_request

        return handle_learn_queue_request(body)
    return None
