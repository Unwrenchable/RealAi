"""vuln_triage: read-only, pure-function dependency vulnerability triage.

Takes audit JSON (``npm audit --json`` / ``pnpm audit --json`` v2 shape with a ``vulnerabilities``
map, or a flat list of ``{package, severity, fixed_in, current}`` rows), groups by package and
suggests, per package, an ``override`` (non-major fix; pnpm/npm overrides entry), a ``major-bump``
(semver-major fix; flagged for the owner) or ``no-fix``. It never writes files, never runs a
package manager and never touches the network. It cannot change a lockfile.

Guidance baked in: land fixes one package per PR through CI, never by force-bumping the whole lockfile.

Call:  POST /v1/tools/execute {"name": "vuln_triage", "arguments": {"audit": {...}}}
       or abilities.vuln_triage.run(context={"audit": {...}}) in-process.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

ABILITY = {
    "id": "vuln_triage",
    "name": "vuln_triage",
    "type": "ability",
    "status": "PARTIAL",
    "source": "RealAI hive: recurring bot vulnerability-triage work",
    "dest": "abilities/vuln_triage.py",
    "capabilities": ["vuln_triage", "dependency_audit", "read_only"],
    "secrets_policy": "none",
}

SEVERITY_RANK = {"critical": 4, "high": 3, "moderate": 2, "medium": 2, "low": 1, "info": 0}
MAX_PACKAGES = 5000
PER_PR_NOTE = "land as its own PR through CI; do not force-bump the whole lockfile"


def _sev(v: Any) -> str:
    s = str(v or "low").strip().lower()
    return s if s in SEVERITY_RANK else "low"


def _major(version: Any) -> Optional[int]:
    s = str(version or "").lstrip("^~>=<v ").split(".")[0]
    return int(s) if s.isdigit() else None


def _entry_from_npm(name: str, v: Dict[str, Any]) -> Dict[str, Any]:
    fix = v.get("fixAvailable")
    fix_name = fix_version = None
    is_major = False
    has_fix = bool(fix)
    if isinstance(fix, dict):
        fix_name, fix_version = fix.get("name"), fix.get("version")
        is_major = bool(fix.get("isSemVerMajor"))
    advisories = [x for x in (v.get("via") or []) if isinstance(x, dict)]
    return {
        "package": str(v.get("name") or name), "severity": _sev(v.get("severity")),
        "is_direct": bool(v.get("isDirect")), "advisories": max(1, len(advisories)),
        "has_fix": has_fix, "is_major": is_major,
        "fix_package": fix_name, "fix_version": fix_version, "range": v.get("range"),
    }


def _entry_from_flat(row: Dict[str, Any]) -> Dict[str, Any]:
    cur, fixed = _major(row.get("current")), _major(row.get("fixed_in"))
    return {
        "package": str(row.get("package") or row.get("name") or "unknown"), "severity": _sev(row.get("severity")),
        "is_direct": bool(row.get("is_direct")), "advisories": 1,
        "has_fix": bool(row.get("fixed_in")), "is_major": bool(cur is not None and fixed is not None and fixed > cur),
        "fix_package": None, "fix_version": row.get("fixed_in"), "range": None,
    }


def _normalise(audit: Any) -> List[Dict[str, Any]]:
    if isinstance(audit, dict) and isinstance(audit.get("vulnerabilities"), dict):
        return [_entry_from_npm(k, v) for k, v in list(audit["vulnerabilities"].items())[:MAX_PACKAGES] if isinstance(v, dict)]
    rows = audit.get("rows") if isinstance(audit, dict) else audit
    if isinstance(rows, list):
        return [_entry_from_flat(r) for r in rows[:MAX_PACKAGES] if isinstance(r, dict)]
    raise ValueError("audit must be npm-audit JSON ({vulnerabilities: {...}}) or a list of rows")


def triage(audit: Any) -> Dict[str, Any]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for e in _normalise(audit):
        g = grouped.setdefault(e["package"], dict(e, advisories=0))
        g["advisories"] += e["advisories"]
        if SEVERITY_RANK[e["severity"]] > SEVERITY_RANK[g["severity"]]:
            g["severity"] = e["severity"]
        g["is_direct"] = g["is_direct"] or e["is_direct"]
        g["has_fix"] = g["has_fix"] or e["has_fix"]
        g["is_major"] = g["is_major"] or e["is_major"]
        g["fix_version"] = g["fix_version"] or e["fix_version"]
        g["fix_package"] = g["fix_package"] or e["fix_package"]

    packages: List[Dict[str, Any]] = []
    overrides: Dict[str, str] = {}
    for name, g in grouped.items():
        target = g["fix_package"] or name
        if not g["has_fix"]:
            action, flag = "no-fix", True
            note = "no fix published; owner decides: accept risk, replace the package, or pin and monitor"
        elif g["is_major"]:
            action, flag = "major-bump", True
            ver = f" to {g['fix_version']}" if g["fix_version"] else ""
            note = f"bump {target}{ver} (semver-major, may break code); owner approval needed, then " + PER_PR_NOTE
        else:
            action, flag = "override", False
            if g["fix_version"] and target == name:
                overrides[name] = f">={g['fix_version']}"
            note = (f"add an overrides entry for {target}"
                    + (f" >= {g['fix_version']}" if g["fix_version"] else "") + "; " + PER_PR_NOTE)
        packages.append({
            "package": name, "severity": g["severity"], "advisories": g["advisories"], "is_direct": g["is_direct"],
            "action": action, "owner_flag": flag, "fix_version": g["fix_version"], "suggestion": note,
        })
    packages.sort(key=lambda p: (-SEVERITY_RANK[p["severity"]], p["package"]))
    summary = {"packages": len(packages),
               "override": sum(p["action"] == "override" for p in packages),
               "major_bump": sum(p["action"] == "major-bump" for p in packages),
               "no_fix": sum(p["action"] == "no-fix" for p in packages),
               "owner_flagged": sum(p["owner_flag"] for p in packages)}
    return {"ok": True, "ability": "vuln_triage", "read_only": True, "summary": summary,
            "packages": packages, "suggested_overrides": dict(sorted(overrides.items()))}


def run(input: str = "", context: Dict[str, Any] | None = None, **kwargs: Any) -> Dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    audit = ctx.get("audit")
    if audit is None and input:
        try:
            audit = json.loads(input)
        except (ValueError, TypeError):
            audit = None
    if isinstance(audit, dict) and "audit" in audit and "vulnerabilities" not in audit:
        audit = audit["audit"]
    if audit is None:
        return {"ok": False, "ability": "vuln_triage", "error": "pass audit=<npm audit --json output>"}
    try:
        return triage(audit)
    except (ValueError, TypeError, AttributeError) as exc:
        return {"ok": False, "ability": "vuln_triage", "error": f"{type(exc).__name__}: {exc}"}
