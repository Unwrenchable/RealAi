"""Operator-triggered Console verify pack.

One short PASS/FAIL report for chat:
hive GET /health, a cheap orch presence check, in-memory LIVE count,
and whether console.html / the operator directive / OPERATOR_MEMORY exist.

Not a Natural Mode turn tool. Core desk and ``ability.console_verify_pack``
only. Does not call ``build_catalog`` and does not start the orchestrator.
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any

ABILITY = {
    "id": "console_verify_pack",
    "name": "console_verify_pack",
    "type": "ability",
    "status": "LIVE",
    "source": "docs/CONSOLE_OPERATOR_DIRECTIVE.md",
    "dest": "abilities/console_verify_pack.py",
    "capabilities": ["verify", "hive_health", "operator_files"],
    "secrets_policy": "none",
    "trigger": "operator",
}

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_TIMEOUT = 1.5
_MAX_TIMEOUT = 2.5
_HEALTH_READ = 800


def _base() -> str:
    return (
        os.environ.get("REALAI_API_BASE")
        or os.environ.get("REALAI_PROVIDER_URL")
        or "http://127.0.0.1:8001"
    ).rstrip("/")


def _timeout(ctx: dict[str, Any]) -> float:
    raw = ctx.get("timeout", _DEFAULT_TIMEOUT)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = _DEFAULT_TIMEOUT
    if value <= 0:
        value = _DEFAULT_TIMEOUT
    return min(value, _MAX_TIMEOUT)


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(_ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _clip(text: str, limit: int = 160) -> str:
    raw = " ".join(str(text or "").split())
    if len(raw) <= limit:
        return raw
    return raw[: limit - 1].rstrip() + "..."


def hive_health(*, timeout: float = _DEFAULT_TIMEOUT) -> dict[str, Any]:
    """GET {REALAI_API_BASE}/health. Down or slow hive is FAIL, not a hang."""
    url = _base() + "/health"
    try:
        req = urllib.request.Request(
            url,
            method="GET",
            headers={"User-Agent": "RealAI-console-verify-pack/1.0"},
        )
        with urllib.request.urlopen(req, timeout=float(timeout)) as resp:
            status = int(getattr(resp, "status", 200) or 200)
            raw = resp.read(_HEALTH_READ).decode("utf-8", "replace")
        http_ok = 200 <= status < 300
        flag = ""
        try:
            payload = json.loads(raw) if raw else {}
            if isinstance(payload, dict):
                flag = str(payload.get("status") or "").strip().lower()
        except Exception:
            flag = ""
        detail = str(status)
        if flag:
            detail += " " + flag
        detail += " " + url
        return {
            "name": "hive",
            "ok": http_ok,
            "status": status,
            "url": url,
            "body_status": flag,
            "line": f"hive {'PASS' if http_ok else 'FAIL'} {detail}",
        }
    except Exception as exc:
        kind = type(exc).__name__
        return {
            "name": "hive",
            "ok": False,
            "url": url,
            "error": _clip(f"{kind}: {exc}"),
            "guarded": True,
            "line": f"hive FAIL {url} ({_clip(f'{kind}: {exc}')})",
        }


def orch_cheap() -> dict[str, Any]:
    """Local orch presence. No second /health GET and no server start.

    Uses the orchestration surface inventory when that module imports.
    Otherwise stats ``realai/orchestration/v3_orchestrator.py``.
    """
    try:
        from abilities.orchestration_surface import run as orch_run

        inv = orch_run(input="", context={"action": "list"})
        modules = inv.get("modules") if isinstance(inv, dict) else None
        v3 = next(
            (row for row in (modules or []) if isinstance(row, dict) and row.get("id") == "v3"),
            None,
        )
        if isinstance(v3, dict):
            present = bool(v3.get("present"))
            detail = str(v3.get("file") or "v3_orchestrator.py")
            if present:
                detail += f" ({int(v3.get('bytes') or 0)} bytes)"
            return {
                "name": "orch",
                "ok": present,
                "cheap": True,
                "present": present,
                "line": f"orch {'PASS' if present else 'FAIL'} {detail}",
            }
    except Exception:
        pass
    path = _ROOT / "realai" / "orchestration" / "v3_orchestrator.py"
    try:
        present = path.is_file()
    except OSError as exc:
        return {
            "name": "orch",
            "ok": False,
            "skipped": True,
            "cheap": True,
            "error": _clip(exc),
            "line": f"orch SKIP unavailable ({_clip(exc)})",
        }
    detail = "realai/orchestration/v3_orchestrator.py"
    if present:
        try:
            detail += f" ({path.stat().st_size} bytes)"
        except OSError:
            pass
    return {
        "name": "orch",
        "ok": present,
        "cheap": True,
        "present": present,
        "line": f"orch {'PASS' if present else 'FAIL'} {detail}",
    }


def coverage_live_count() -> dict[str, Any]:
    """Count LIVE rows on the in-memory rundown. Never calls build_catalog."""
    try:
        from realai.ability_catalog import RUNDOWN_ABILITIES
    except Exception as exc:
        return {
            "name": "coverage",
            "ok": True,
            "skipped": True,
            "cheap": False,
            "error": _clip(exc),
            "line": f"coverage SKIP not cheap ({_clip(exc)})",
        }
    live = sum(
        1
        for row in RUNDOWN_ABILITIES
        if str((row or {}).get("status") or "").upper() == "LIVE"
    )
    return {
        "name": "coverage",
        "ok": live > 0,
        "cheap": True,
        "live_count": live,
        "line": f"coverage {'PASS' if live > 0 else 'FAIL'} LIVE={live}",
    }


def _path_check(name: str, loader: str, fallback_rel: str) -> dict[str, Any]:
    path: Path | None
    try:
        from realai.bot import boot

        found = getattr(boot, loader)()
        path = found if isinstance(found, Path) else None
    except Exception:
        candidate = _ROOT / fallback_rel
        path = candidate if candidate.is_file() else None
    if path is None or not path.is_file():
        return {
            "name": name,
            "ok": False,
            "line": f"{name} FAIL missing {fallback_rel}",
        }
    return {
        "name": name,
        "ok": True,
        "path": _rel(path),
        "line": f"{name} PASS {_rel(path)}",
    }


def console_copies() -> dict[str, Any]:
    web = _ROOT / "apps" / "vscode" / "webview" / "console.html"
    prod = _ROOT / "console.html"
    web_ok = web.is_file()
    prod_ok = prod.is_file()
    if not web_ok or not prod_ok:
        missing = []
        if not web_ok:
            missing.append("apps/vscode/webview/console.html")
        if not prod_ok:
            missing.append("console.html")
        return {
            "name": "console.html",
            "ok": False,
            "line": "console.html FAIL missing " + ", ".join(missing),
        }
    try:
        same = web.read_bytes() == prod.read_bytes()
    except OSError as exc:
        return {
            "name": "console.html",
            "ok": False,
            "line": f"console.html FAIL unreadable ({_clip(exc)})",
        }
    if not same:
        return {
            "name": "console.html",
            "ok": False,
            "line": "console.html FAIL copies differ",
        }
    return {
        "name": "console.html",
        "ok": True,
        "line": "console.html PASS",
    }


def _hard(check: dict[str, Any]) -> bool:
    if check.get("skipped"):
        return True
    return bool(check.get("ok"))


def format_report(checks: list[dict[str, Any]]) -> tuple[bool, str]:
    ok = all(_hard(row) for row in checks)
    verdict = "PASS" if ok else "FAIL"
    lines = [row.get("line") or "" for row in checks]
    text = "VERIFY " + verdict + "\n" + "\n".join(line for line in lines if line)
    return ok, text


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    timeout = _timeout(ctx)
    checks = [
        hive_health(timeout=timeout),
        orch_cheap(),
        coverage_live_count(),
        console_copies(),
        _path_check(
            "operator directive",
            "operator_directive_path",
            "docs/CONSOLE_OPERATOR_DIRECTIVE.md",
        ),
        _path_check(
            "OPERATOR_MEMORY",
            "operator_memory_path",
            "docs/OPERATOR_MEMORY.md",
        ),
    ]
    ok, report = format_report(checks)
    return {
        "ok": ok,
        "ability": "console_verify_pack",
        "verdict": "PASS" if ok else "FAIL",
        "report": report,
        "checks": checks,
        "triggered": "operator",
        "every_turn": False,
        "timeout": timeout,
        "input": input,
        "note": (
            "Operator-triggered verify pack. Not a Natural Mode turn tool. "
            "Hive down is FAIL and does not hang."
        ),
    }
