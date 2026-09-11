"""
Living RealAI self-check — what you actually *run*, not recovered archives.

Recovered snapshots under recovered/ are a museum of past branches.
This doctor only validates the living product tree so RealAI can serve,
use its CLI, and improve itself.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _ok(name: str, detail: str = "") -> dict[str, Any]:
    return {"name": name, "ok": True, "detail": detail}


def _fail(name: str, detail: str) -> dict[str, Any]:
    return {"name": name, "ok": False, "detail": detail}


def _try_import(mod: str) -> tuple[bool, str]:
    try:
        m = importlib.import_module(mod)
        return True, getattr(m, "__file__", mod) or mod
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def run_doctor(*, json_mode: bool = False) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    # Core package
    ok, detail = _try_import("realai")
    checks.append(_ok("import.realai", detail) if ok else _fail("import.realai", detail))

    ok, detail = _try_import("realai.api_server")
    checks.append(_ok("import.api_server", detail) if ok else _fail("import.api_server", detail))

    ok, detail = _try_import("realai.router")
    checks.append(_ok("import.router", detail) if ok else _fail("import.router", detail))

    # Self-work surfaces
    for mod, label in (
        ("realai.self_improvement", "self_improvement"),
        ("realai.ability_catalog", "ability_catalog"),
        ("realai.cli.realai_cli", "cli"),
    ):
        ok, detail = _try_import(mod)
        checks.append(_ok(f"import.{label}", detail) if ok else _fail(f"import.{label}", detail))

    # Organs hive (living cognition)
    try:
        from modules.organs import hive_status

        st = hive_status()
        n = int(st.get("organ_count") or 0)
        if n >= 44:
            checks.append(_ok("organs.hive", f"organ_count={n} complete={st.get('complete')}"))
        else:
            checks.append(_fail("organs.hive", f"organ_count={n} expected>=44"))
    except Exception as e:
        checks.append(_fail("organs.hive", f"{type(e).__name__}: {e}"))

    # RackUp intelligence provider
    try:
        from plugins.rackup_coach import METADATA, invoke

        ver = METADATA.get("version")
        r = invoke(
            {
                "ability": "roc_info",
                "player": {"player_id": "doctor"},
                "payload": {},
                "organs_enabled": False,
            }
        )
        checks.append(
            _ok(
                "rackup_coach",
                f"version={ver} roc_info_ok={r.get('ok')} ladder={METADATA.get('roc', {}).get('ladder')}",
            )
        )
    except Exception as e:
        checks.append(_fail("rackup_coach", f"{type(e).__name__}: {e}"))

    # Glicko ladder present
    ok, detail = _try_import("plugins.rackup_coach.glicko2")
    checks.append(_ok("glicko2", detail) if ok else _fail("glicko2", detail))

    # Money audit present (read-only)
    ok, detail = _try_import("plugins.rackup_coach.money_audit")
    checks.append(_ok("money_audit", detail) if ok else _fail("money_audit", detail))

    # Living layout: product root (C:\RealAI-clean) and package (...\realai)
    living_rel = (
        "core/",
        "modules/",
        "plugins/rackup_coach/",
        "registry/",
        "adapters/",
        "api_server.py",
        "requirements.txt",
    )
    search_roots = [ROOT]
    pkg = ROOT / "realai"
    if pkg.is_dir():
        search_roots.append(pkg)
    try:
        from realai.workspace import product_root, realai_home
        for extra in (Path(product_root()), Path(realai_home())):
            if extra not in search_roots:
                search_roots.append(extra)
    except Exception:
        pass
    for label in living_rel:
        rel = label.replace("/", "\\").strip("\\")
        hit = None
        for base in search_roots:
            cand = base / rel
            if cand.exists():
                hit = cand
                break
        if hit is not None:
            checks.append(_ok(f"path.{label}", str(hit)))
        else:
            tried = ", ".join(str(b / rel) for b in search_roots)
            checks.append(_fail(f"path.{label}", f"missing ({tried})"))

    # Archive vs product boundary
    recovered = ROOT / "recovered"
    if recovered.is_dir():
        n_snap = sum(1 for d in recovered.iterdir() if d.is_dir())
        checks.append(
            _ok(
                "archive.recovered",
                f"{n_snap} snapshot dirs — ARCHIVE only, not required to run the product",
            )
        )
    else:
        checks.append(_ok("archive.recovered", "no recovered/ (fine for lean deploy)"))

    # Ability catalog coverage (best-effort)
    try:
        from realai.ability_catalog import build_catalog, coverage_summary

        cat = build_catalog()
        cov = coverage_summary()
        c = (cov.get("coverage") or {})
        checks.append(
            _ok(
                "ability_catalog",
                f"weighted={c.get('weighted_pct')}% live={c.get('live_count')} "
                f"abilities={len(cat.get('abilities') or cat.get('items') or [])}",
            )
        )
    except Exception as e:
        checks.append(_fail("ability_catalog", f"{type(e).__name__}: {e}"))

    failed = [c for c in checks if not c["ok"]]
    report = {
        "product": "RealAI living provider",
        "branch_hint": "unification/ultimate-all",
        "root": str(ROOT),
        "python": sys.version.split()[0],
        "ok": len(failed) == 0,
        "passed": sum(1 for c in checks if c["ok"]),
        "failed": len(failed),
        "checks": checks,
        "how_to_run": {
            "doctor": "python -m realai doctor",
            "serve": "python -m realai serve",
            "cli_help": "python -m realai --help",
            "api_alt": "python api_server.py",
        },
        "boundary": {
            "living_product": [
                "realai/",
                "core/",
                "modules/",
                "plugins/",
                "registry/",
                "adapters/",
                "server/",
                "api_server.py",
            ],
            "archive_only_do_not_run_as_product": [
                "recovered/*",
                "remote recovery/* branches",
                "60 historical tips",
            ],
            "note": (
                "Snapshots preserve unique code so nothing is lost. "
                "They are not 60 competing products — the living tree is the product."
            ),
        },
    }
    if json_mode:
        return report

    # human print
    print("RealAI living doctor")
    print(f"  root: {ROOT}")
    print(f"  python: {sys.version.split()[0]}")
    print()
    for c in checks:
        mark = "OK " if c["ok"] else "FAIL"
        print(f"  [{mark}] {c['name']}: {c['detail']}")
    print()
    if failed:
        print(f"RESULT: NOT READY ({len(failed)} failed)")
        print("Fix failed imports/paths on the living tree — ignore recovered/ for runtime.")
    else:
        print("RESULT: READY — living product can import, serve, and self-check.")
        print("  python -m realai serve")
        print("  python -m realai catalog")
    print()
    print("Archive (recovered/) is a library of past branches, not the app.")
    return report
