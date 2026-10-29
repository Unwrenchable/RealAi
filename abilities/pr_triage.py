"""pr_triage: read-only, pure-function pull request triage.

No network, no file writes, no merge/approve/comment powers. Give it PR facts (for example the JSON
from ``gh pr view --json state,isDraft,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup``
or ``gh pr checks --json name,state,bucket``) and it returns a verdict plus a reason:

    mergeable | needs-rebase | failing-check | needs-owner

Call:  POST /v1/tools/execute {"name": "pr_triage", "arguments": {"pr": {...}}}
       or abilities.pr_triage.run(context={"pr": {...}}) in-process.

Input ``pr`` keys (all optional, case-insensitive values): state (OPEN|CLOSED|MERGED), isDraft/draft,
mergeable (MERGEABLE|CONFLICTING|UNKNOWN), mergeStateStatus (CLEAN|BEHIND|DIRTY|BLOCKED|UNSTABLE|...),
reviewDecision, checks (or statusCheckRollup): list of {name, state|conclusion|status|bucket}.
The verdict never merges anything: it only says whether the owner's merge rule (all checks passed,
no conflicts with base) is satisfied.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

ABILITY = {
    "id": "pr_triage",
    "name": "pr_triage",
    "type": "ability",
    "status": "LIVE",
    "source": "RealAI hive: recurring bot PR-triage work",
    "dest": "abilities/pr_triage.py",
    "capabilities": ["pr_triage", "merge_readiness", "read_only"],
    "secrets_policy": "none",
}

VERDICTS = ("mergeable", "needs-rebase", "failing-check", "needs-owner")
_FAIL = {"FAILURE", "FAILED", "FAIL", "ERROR", "TIMED_OUT", "CANCELLED", "CANCEL", "ACTION_REQUIRED", "STARTUP_FAILURE"}
_PENDING = {"PENDING", "QUEUED", "IN_PROGRESS", "WAITING", "REQUESTED", "EXPECTED", "RUNNING"}
_PASS = {"SUCCESS", "PASSED", "PASS", "NEUTRAL", "SKIPPED", "SKIPPING", "COMPLETED"}
MAX_CHECKS = 500


def _up(v: Any) -> str:
    return str(v).strip().upper() if v is not None else ""


def _check_state(chk: Dict[str, Any]) -> str:
    """Normalise one check to PASS | FAIL | PENDING."""
    for key in ("bucket", "conclusion", "state", "status"):
        val = _up(chk.get(key))
        if not val:
            continue
        if val in _FAIL:
            return "FAIL"
        if val in _PENDING:
            return "PENDING"
        if val in _PASS and not (key == "status" and val == "COMPLETED" and chk.get("conclusion")):
            return "PASS"
    return "PENDING"


def _result(verdict: str, reason: str, **extra: Any) -> Dict[str, Any]:
    return {"ok": True, "ability": "pr_triage", "verdict": verdict, "reason": reason, "read_only": True, **extra}


def triage(pr: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(pr, dict):
        raise ValueError("pr must be an object")
    state = _up(pr.get("state")) or "OPEN"
    if state != "OPEN":
        return _result("needs-owner", f"PR is {state.lower()}; nothing to merge")
    if pr.get("isDraft") or pr.get("draft"):
        return _result("needs-owner", "PR is a draft; owner must mark it ready")

    merge_state = _up(pr.get("mergeStateStatus"))
    mergeable = _up(pr.get("mergeable"))
    if mergeable == "CONFLICTING" or merge_state == "DIRTY":
        return _result("needs-rebase", "conflicts with base; merge the base into the branch and re-run checks")
    if merge_state == "BEHIND":
        return _result("needs-rebase", "branch is behind base; update it from base and re-run checks")

    raw = pr.get("checks")
    if raw is None:
        raw = pr.get("statusCheckRollup")
    checks: List[Dict[str, Any]] = [c for c in (raw or [])[:MAX_CHECKS] if isinstance(c, dict)]
    failing = sorted({str(c.get("name") or c.get("context") or "unnamed") for c in checks if _check_state(c) == "FAIL"})
    pending = [c for c in checks if _check_state(c) == "PENDING"]
    if failing:
        return _result("failing-check", "failing: " + ", ".join(failing[:10]), failing=failing[:10])
    if _up(pr.get("reviewDecision")) == "CHANGES_REQUESTED":
        return _result("needs-owner", "a reviewer requested changes")
    if not checks:
        return _result("needs-owner", "no checks reported; cannot confirm all checks passed")
    if pending:
        return _result("needs-owner", f"{len(pending)} check(s) still pending; wait for them to finish")
    if merge_state == "BLOCKED":
        return _result("needs-owner", "checks pass but branch protection blocks the merge (review or rule)")
    if mergeable == "UNKNOWN":
        return _result("needs-owner", "GitHub has not computed mergeability yet; re-check shortly")
    return _result("mergeable", "all checks passed and no conflicts with base")


def run(input: str = "", context: Dict[str, Any] | None = None, **kwargs: Any) -> Dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    pr: Optional[Any] = ctx.get("pr")
    if pr is None and input:
        try:
            parsed = json.loads(input)
            pr = parsed.get("pr", parsed) if isinstance(parsed, dict) else None
        except (ValueError, TypeError):
            pr = None
    if not isinstance(pr, dict):
        return {"ok": False, "ability": "pr_triage", "error": "pass pr={state, mergeable, mergeStateStatus, checks, ...}"}
    try:
        return triage(pr)
    except (ValueError, TypeError) as exc:
        return {"ok": False, "ability": "pr_triage", "error": f"{type(exc).__name__}: {exc}"}
