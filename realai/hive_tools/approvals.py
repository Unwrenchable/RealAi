"""request_approval: the ONLY write/exec surface the hive / self_data loop sees.

It files a pending request with realai.core.approval_gate (dry-run preview, workspace-scoped, audited) and returns
its id. It never executes: there is deliberately no execute/approve tool here. A human approves in the approval UI
and runs it (``python -m realai.core.approval_gate execute <id>``).

self_data / spotcheck (offline=True) write to a private temp approvals store, so training rows never land in the
real queue; the live tool loop (offline=False, REALAI_HIVE_TOOLS=1) files into the real store.
Verifiable contract: result.status is "pending" (or "refused" for money / out-of-workspace / protected paths) and
result.executed is False; recomputing gives the identical request (content-hashed id, idempotent).
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from realai.hive_tools.extended import _fn

_S = {"type": "string"}
_SANDBOX: Dict[str, Path] = {}

SPECS: Dict[str, Dict[str, Any]] = {
    "request_approval": _fn(
        "request_approval",
        "Ask Travis to approve a write/exec action on this workspace. Fields per action: search_replace: file_path, "
        "old_string, new_string; write_file: file_path, content; run_terminal_command: command (cwd optional); "
        "run_script: code (language optional, default python); auto_wire / self_heal_promote / self_extend / "
        "self_repair: reason only; trade_execute: proposal_id from trade_propose. Files a PENDING request with a dry-run "
        "preview; nothing runs until a human approves. Say pending only if status is pending; if refused, say why. Raw "
        "sends/transfers/payouts are refused. Not for delegating work to agents (use route_to_agent).",
        {"action": {"type": "string", "enum": ["search_replace", "write_file", "run_terminal_command", "run_script",
                                               "auto_wire", "self_heal_promote", "self_extend", "self_repair", "trade_execute"]},
         "file_path": _S, "old_string": _S, "new_string": _S, "content": _S, "command": _S, "cwd": _S,
         "code": _S, "language": _S, "proposal_id": _S, "reason": _S},
        ["action", "reason"]),
}


def _sandbox_store() -> Path:
    if "p" not in _SANDBOX:
        _SANDBOX["p"] = Path(tempfile.mkdtemp(prefix="realai-approvals-sandbox-")) / ".approvals.json"
    return _SANDBOX["p"]


def request_approval(args: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    from realai.core import approval_gate

    action = str(args.get("action") or "").strip()
    reason = str(args.get("reason") or "")
    payload = {k: v for k, v in args.items() if k not in ("action", "reason", "approved", "approval_id")}
    if not ctx.get("approvals_sandbox"):
        r = approval_gate.request(action, payload, requested_by="hive", reason=reason)
    else:
        keep = {k: os.environ.get(k) for k in ("REALAI_APPROVALS_STORE", "REALAI_APPROVALS_AUDIT", "REALAI_TRADE_BACKEND",
                                               "REALAI_TRADE_MODE", "REALAI_TRADE_KILL_FILE")}
        store = _sandbox_store()
        os.environ["REALAI_APPROVALS_STORE"] = str(store)
        os.environ["REALAI_APPROVALS_AUDIT"] = str(store.with_suffix(".audit.jsonl"))
        # trade cards in the sandbox: simulator previews only, never the real CLI, never the real kill file
        os.environ["REALAI_TRADE_BACKEND"] = "sim"
        os.environ["REALAI_TRADE_MODE"] = "1"
        os.environ["REALAI_TRADE_KILL_FILE"] = str(store.with_name("KILL"))
        try:
            r = approval_gate.request(action, payload, requested_by="hive-sandbox", reason=reason)
        finally:
            for k, v in keep.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    r.pop("note", None)
    r["executed"] = False
    r["next_step"] = "waiting for human approval" if r.get("status") == "pending" else "not filed"
    return r


EXECUTORS = {"request_approval": request_approval}


def key_facts(name: str, r: Dict[str, Any], args: Dict[str, Any]) -> List[List[str]]:
    if r.get("status") == "pending":
        return [["pending", "approval", "approve"]]
    return [["refused", "can't", "cannot", "not allowed", "locked", "won't", "outside", "protected", "not found"]]


def contract_violation(r: Dict[str, Any]) -> str:
    """'' if the result honours request-only behaviour, else a reason (used by self_data verify)."""
    if r.get("executed") or r.get("status") not in ("pending", "refused"):
        return "approval_executed_or_bypassed"
    return ""
