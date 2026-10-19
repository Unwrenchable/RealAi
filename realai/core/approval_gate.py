"""Approval gate for write / exec actions (deny by default).

Models, agents and the hive may REQUEST a side-effecting action. Nothing runs at request time: the gate
validates the request, computes a dry-run preview (unified diff for edits, exact argv/cwd for commands,
the tool's own dry-run report for self-heal / auto-wire / self-extend / self-repair) and stores a pending
item in the existing approvals store (``.approvals.json``, the same file ``approval_status`` and the approval
UI read). A human approves in the approval UI (or ``python -m realai.core.approval_gate approve <id>``,
which asks for interactive confirmation). Only then can ``execute(<id>)`` run it - once.

Guarantees
  * deny by default: anything not ``status == "approved"`` is refused; executed items cannot run twice
  * stale-safe: the preview hash is re-checked at execution (file changed since the request -> refused)
  * workspace-scoped: paths must resolve inside the workspace; protected paths (.git, .env, keys, wallets,
    the approvals store and audit log themselves) are refused at request time
  * audit log: every request / refusal / approval / execution appends a JSON line (``<store>.audit.jsonl``)
  * money stays separately locked: sends / transfers / payouts / wallet signing are refused outright here,
    approved or not (they need their own explicit path, which this module never provides)
  * trade_execute (trade mode) is that one explicit path, and only for a stored DRY-RUN swap proposal of the local
    Node CLI (C:\tools\realai): the card shows the CLI's preview (amount, USD, slippage, min-out, route, impact, caps,
    safety verdict) and is refused at request time when anything breaks a cap, the bot wallet / Solana rule, the
    safety check, or the kill switch. Executing an approved card hands a one-time ticket (the approval id) to
    ``realai trade execute <proposal> --live --realai-ticket <id>``; the CLI re-reads this store (read-only), checks
    status/TTL (60-120 s from the approval)/hash/caps/kill switch, re-quotes and aborts on drift, then applies all of
    its own live gates (profile, trading.live, risk engine, DEX guards, pre-flight). Free-form commands, raw sends,
    transfers and key access stay refused/pending exactly as before.

Env: REALAI_APPROVALS_STORE / APPROVALS_STORE (store path; default from realai.core.approvals_config), REALAI_APPROVALS_AUDIT (audit path),
REALAI_WORKSPACE / REALAI_HOME (workspace root).
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ACTIONS = ("search_replace", "write_file", "run_terminal_command", "run_script", "auto_wire", "self_heal_promote",
           "self_heal_curated_promote", "self_heal_deep_promote", "self_extend", "self_repair", "trade_execute")
EXEC_TIMEOUT_S = 300
MONEY = re.compile(r"(send[_ -]?(sol|transaction|tx|funds|payment)|sign[_ -]?and[_ -]?send|transfer[_ -]?(sol|token|funds)|"
                   r"spl-token\s+transfer|solana\s+transfer|stripe|payout|release[_ -]?payment|private[_ -]?key|"
                   r"seed[_ -]?phrase|mnemonic|keypair|wallet\.sign)", re.I)
PROTECTED = re.compile(r"(^|/)(\.git|\.env[^/]*|keys?|secrets?|wallets?|\.ssh)(/|$)|\.(pem|key|p12|pfx)$|id_rsa|"
                       r"\.approvals\.json|approvals[^/]*\.audit\.jsonl", re.I)


# ----------------------------------------------------------------------------- locations
def workspace() -> Path:
    return Path(os.environ.get("REALAI_WORKSPACE") or os.environ.get("REALAI_HOME") or Path.cwd()).resolve()


def store_path() -> Path:
    """The one approvals store (see realai.core.approvals_config): env, then config/approvals.json, then
    C:\\RealAI-clean\\.approvals.json on Windows / a temp store elsewhere."""
    from realai.core.approvals_config import store_path as _sp

    return _sp()


def audit_path() -> Path:
    env = os.environ.get("REALAI_APPROVALS_AUDIT")
    return Path(env) if env else store_path().with_name(store_path().name + ".audit.jsonl")


def _load() -> Dict[str, Any]:
    p = store_path()
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {"items": []}
    except (OSError, json.JSONDecodeError):
        return {"items": []}


def _save(data: Dict[str, Any]) -> None:
    p = store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def audit(event: str, **fields: Any) -> None:
    rec = {"ts": round(time.time(), 3), "event": event, **fields}
    try:
        p = audit_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
    except OSError:
        pass


def _sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


# ----------------------------------------------------------------------------- validation + previews
class Refused(Exception):
    pass


def resolve_in_workspace(rel: str) -> Path:
    if not str(rel or "").strip():
        raise Refused("path required")
    ws = workspace()
    p = (ws / rel).resolve() if not Path(rel).is_absolute() else Path(rel).resolve()
    try:
        relp = p.relative_to(ws).as_posix()
    except ValueError:
        raise Refused(f"path outside workspace: {rel}")
    if PROTECTED.search(relp):
        raise Refused(f"protected path: {relp}")
    return p


def _money_check(action: str, args: Dict[str, Any]) -> None:
    if MONEY.search(action) or MONEY.search(json.dumps(args, default=str)):
        raise Refused("money_locked: sends/transfers/payouts/wallet signing are not available through approvals")


def _preview_edit(args: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    path = resolve_in_workspace(str(args.get("file_path") or args.get("path") or ""))
    old, new = str(args.get("old_string") or ""), str(args.get("new_string") or "")
    if not path.is_file():
        raise Refused("not a file")
    raw = path.read_text(encoding="utf-8", errors="replace")
    if not old:
        raise Refused("old_string required")
    n = raw.count(old)
    if n == 0:
        raise Refused("old_string not found")
    if n > 1 and not args.get("replace_all"):
        raise Refused(f"old_string matches {n} times; pass replace_all or a longer old_string")
    updated = raw.replace(old, new) if args.get("replace_all") else raw.replace(old, new, 1)
    rel = path.relative_to(workspace()).as_posix()
    diff = "".join(difflib.unified_diff(raw.splitlines(True), updated.splitlines(True), f"a/{rel}", f"b/{rel}"))
    norm = {"file_path": rel, "old_string": old, "new_string": new, "replace_all": bool(args.get("replace_all"))}
    return norm, {"kind": "diff", "file": rel, "diff": diff[:20000], "matches": n,
                  "file_sha256": hashlib.sha256(raw.encode()).hexdigest()}


def _preview_write(args: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    path = resolve_in_workspace(str(args.get("file_path") or args.get("path") or ""))
    content = str(args.get("content") or "")
    rel = path.relative_to(workspace()).as_posix()
    raw = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    diff = "".join(difflib.unified_diff(raw.splitlines(True), content.splitlines(True), f"a/{rel}", f"b/{rel}"))
    return {"file_path": rel, "content": content}, {"kind": "diff", "file": rel, "diff": diff[:20000], "creates": not path.exists(),
                                                     "file_sha256": hashlib.sha256(raw.encode()).hexdigest()}


def _preview_command(args: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    cmd = str(args.get("command") or args.get("cmd") or "").strip()
    if not cmd:
        raise Refused("command required")
    if re.search(r"approvals", cmd, re.I):
        raise Refused("commands may not touch the approvals store")
    cwd = resolve_in_workspace(str(args.get("cwd") or ".")) if args.get("cwd") else workspace()
    timeout = max(1, min(int(args.get("timeout") or 60), EXEC_TIMEOUT_S))
    shell = ["cmd.exe", "/d", "/s", "/c", cmd] if os.name == "nt" else ["bash", "-lc", cmd]
    rel_cwd = cwd.relative_to(workspace()).as_posix() or "."
    return {"command": cmd, "cwd": rel_cwd, "timeout": timeout}, {"kind": "command", "argv": shell, "cwd": rel_cwd,
                                                                   "timeout_s": timeout}


TOOL_PLANS: Dict[str, Dict[str, Any]] = {
    "auto_wire": {"runs": "abilities.auto_wire.main()", "reads": "auto_wire.SEARCH_ROOTS (*.py, AST/regex only)",
                  "writes": "auto_wire.ABILITY_REGISTRY (ability/tool/task registry JSON)"},
    "self_heal_promote": {"runs": "scan_results promote_gold.py --apply (falls back to curated promote)",
                          "writes": "promoted files listed in scan_results/promote_queue.json", "requires": "REALAI_SELF_IMPROVE=1"},
    "self_heal_curated_promote": {"runs": "scripts/curated_promote.py --apply", "writes": "curated allowlist targets",
                                  "requires": "REALAI_SELF_IMPROVE=1"},
    "self_heal_deep_promote": {"runs": "deep promote --apply", "writes": "deep-gold promote targets",
                               "requires": "REALAI_SELF_IMPROVE=1"},
    "self_extend": {"runs": "realai.server.tools.self_extend_tool.run", "writes": "ability catalog (save_catalog)"},
    "self_repair": {"runs": "realai.server.tools.self_repair_tool.run",
                    "writes": "mkdir logs/ training/data/ scan_results/ models/ under REALAI_HOME; ability catalog; env defaults"},
}


def _preview_tool(action: str, args: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Static, deterministic plan (the tools have no side-effect-free dry run, so nothing is called here)."""
    if action not in TOOL_PLANS:
        raise Refused(f"unknown action {action}")
    norm = {k: v for k, v in args.items() if k in ("goal", "issue", "input", "force", "reason")}
    return norm, {"kind": "plan", "plan": TOOL_PLANS[action], "args": norm}


def _preview_script(args: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    lang = str(args.get("language") or args.get("lang") or "python").lower()
    code = str(args.get("code") or args.get("source") or "")
    if not code.strip():
        raise Refused("code required")
    fn = str(args.get("filename") or args.get("path") or "")
    if fn:
        resolve_in_workspace(fn)
    argv = [str(a) for a in (args.get("argv") or [])] if isinstance(args.get("argv"), list) else []
    norm = {"language": lang, "code": code, "filename": fn, "argv": argv}
    return norm, {"kind": "script", "language": lang, "filename": fn or "(scratch)", "argv": argv, "code": code[:20000]}


# ----------------------------------------------------------------------------- trade mode (trade_execute)
PROPOSAL_ID = re.compile(r"^prop_[0-9a-f]{10}$")
TRADE_CHAINS = ("solana",)


def trade_mode_enabled() -> bool:
    return os.environ.get("REALAI_TRADE_MODE", "").strip().lower() in ("1", "true", "yes", "on")


def trade_kill_file() -> Path:
    env = os.environ.get("REALAI_TRADE_KILL_FILE")
    if env:
        return Path(env)
    return Path(r"D:\ARCHIVE\trade-journal\KILL") if os.name == "nt" else Path(tempfile.gettempdir()) / "realai-trade-KILL"


def trade_limits() -> Dict[str, float]:
    """Hard ceilings on the Python side (the CLI config caps apply too; the lower one wins)."""
    def f(name: str, default: float) -> float:
        try:
            return float(os.environ.get(name, default))
        except ValueError:
            return default
    return {"max_usd": f("REALAI_TRADE_MAX_USD", 5.0), "max_slippage_bps": f("REALAI_TRADE_MAX_SLIPPAGE_BPS", 300.0)}


def _trade_backend_preview(pid: str) -> Dict[str, Any]:
    from realai.hive_tools import trade as _trade

    if _trade.backend() == "sim":
        return _trade.sim_preview(pid)
    return _trade.run_cli(["trade", "preview", pid, "--json"])


def _preview_trade(args: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    pid = str(args.get("proposal_id") or "").strip()
    if not PROPOSAL_ID.match(pid):
        raise Refused("trade_execute needs proposal_id from trade_propose (prop_xxxxxxxxxx)")
    extra = sorted(k for k in args if k not in ("proposal_id", "reason"))
    if extra:
        raise Refused(f"trade_execute takes only proposal_id (the preview comes from the trading CLI); got {', '.join(extra)}")
    if not trade_mode_enabled():
        raise Refused("trade mode is off (REALAI_TRADE_MODE=1 enables trade_execute cards)")
    if trade_kill_file().exists():
        raise Refused("kill switch is set: no trade cards")
    pv = _trade_backend_preview(pid)
    t = pv.get("preview") or {}
    if not pv.get("previewHash") or not t:
        raise Refused(f"no preview for {pid}: {str(pv.get('error') or 'trading CLI unavailable')[:200]}")
    problems = list(pv.get("problems") or [])
    lim = trade_limits()
    if t.get("chain") not in TRADE_CHAINS:
        problems.append(f"chain {t.get('chain')} not allowed (Solana only)")
    if not (t.get("caps") or {}).get("wallet") or t.get("wallet") != (t.get("caps") or {}).get("wallet"):
        problems.append("bot wallet only")
    usd = t.get("usd")
    if not isinstance(usd, (int, float)) or usd <= 0:
        problems.append("trade cannot be valued in USD")
    elif usd > lim["max_usd"]:
        problems.append(f"usd {usd} > hard cap {lim['max_usd']:g}")
    slip = t.get("slippageBps")
    if not isinstance(slip, (int, float)) or slip > lim["max_slippage_bps"]:
        problems.append(f"slippage {slip} bps > hard cap {lim['max_slippage_bps']:g}")
    if (t.get("safety") or {}).get("required") and (t.get("safety") or {}).get("verdict") != "pass":
        problems.append("token safety check failed")
    if problems:
        raise Refused("trade refused: " + "; ".join(dict.fromkeys(str(p) for p in problems)))
    summary = (f"{t.get('amountIn')} {t.get('inSymbol') or t.get('from')} -> {t.get('outSymbol') or t.get('to')} "
               f"(~${usd:g}) on {t.get('chain')} via {t.get('dex')} [{t.get('route')}], slippage {slip} bps, "
               f"min-out {t.get('minOut')}, impact {t.get('priceImpactBps')} bps, wallet {t.get('wallet')}; caps "
               f"${(t.get('caps') or {}).get('maxTradeUsd')}/trade, ${(t.get('caps') or {}).get('maxDailyUsd')}/day, "
               f"{(t.get('caps') or {}).get('maxDailyTrades')} trades/day; used today {t.get('usedToday')}")
    ttl = max(60, min(120, int(t.get("ticketTtlSec") or 90)))
    return {"proposal_id": pid}, {"kind": "trade", "summary": summary, "trade": t, "preview_hash": pv["previewHash"],
                                  "ticket_ttl_s": ttl, "note": "LIVE trade with real funds on approval. Execute within "
                                  f"{ttl}s of approving; the CLI re-quotes and aborts if the price moved."}


def _run_trade(req_id: str, item: Dict[str, Any], norm: Dict[str, Any], prev: Dict[str, Any]) -> Dict[str, Any]:
    from realai.hive_tools import trade as _trade

    if not trade_mode_enabled():
        raise Refused("trade mode is off")
    if trade_kill_file().exists():
        raise Refused("kill switch is set")
    ttl = int(prev.get("ticket_ttl_s") or 90)
    age = time.time() - float(item.get("decided_at") or 0)
    if age > ttl:
        raise Refused(f"ticket expired ({int(age)}s > {ttl}s since approval); re-propose and re-approve")
    if _trade.backend() == "sim":
        return {"ok": False, "mode": "sim", "error": "simulator: nothing is ever sent"}
    keep = os.environ.get("REALAI_APPROVALS_STORE")
    os.environ["REALAI_APPROVALS_STORE"] = str(store_path())  # the CLI re-reads THIS store (read-only) to verify the ticket
    try:
        res = _trade.run_cli(["trade", "execute", norm["proposal_id"], "--live", "--realai-ticket", req_id, "--json"], timeout=150)
    finally:
        if keep is None:
            os.environ.pop("REALAI_APPROVALS_STORE", None)
        else:
            os.environ["REALAI_APPROVALS_STORE"] = keep
    return {k: res.get(k) for k in ("ok", "mode", "error", "proposalId", "notionalUsd", "txHash", "explorer") if k in res}


PREVIEW: Dict[str, Callable[[Dict[str, Any]], Tuple[Dict[str, Any], Dict[str, Any]]]] = {
    "search_replace": _preview_edit, "write_file": _preview_write, "run_terminal_command": _preview_command,
    "run_script": _preview_script, "trade_execute": _preview_trade}


def preview(action: str, args: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if action not in ACTIONS:
        raise Refused(f"unknown action {action!r}; allowed: {', '.join(ACTIONS)}")
    _money_check(action, args)
    fn = PREVIEW.get(action)
    return fn(args) if fn else _preview_tool(action, args)


# tool names (hive / orchestrator / craft) -> gate action
TOOL_TO_ACTION: Dict[str, str] = {
    **{n: "run_terminal_command" for n in ("run_command", "shell", "hive_exec", "exec_command", "run_terminal_command")},
    **{n: "run_script" for n in ("run_script", "exec_script", "hive_script")},
    **{n: "search_replace" for n in ("search_replace", "str_replace", "edit_file", "apply_edit")},
    **{n: "write_file" for n in ("write_file", "create_file", "workspace_write")},
    "auto_wire": "auto_wire", "ability.auto_wire": "auto_wire",
    "self_heal_promote": "self_heal_promote", "self_heal_promote_apply": "self_heal_promote",
    "self_heal_curated_promote": "self_heal_curated_promote", "self_heal_deep_promote": "self_heal_deep_promote",
    **{n: "self_extend" for n in ("self_extend", "self_extend_tool")},
    **{n: "self_repair" for n in ("self_repair", "self_repair_tool")},
}


def gated_action(tool_name: str) -> Optional[str]:
    """Gate action for a tool name, or None. No escape hatch: console sessions go through the gate too."""
    return TOOL_TO_ACTION.get(tool_name)


def normalize_tool_args(action: str, args: Dict[str, Any]) -> Dict[str, Any]:
    a = dict(args or {})
    if action in ("search_replace", "write_file"):
        a.setdefault("file_path", a.get("target_file") or a.get("path") or a.get("file"))
        a.setdefault("old_string", a.get("old_str") or a.get("old"))
        a.setdefault("new_string", a.get("new_str") or a.get("new"))
        if action == "write_file":
            a.setdefault("content", a.get("contents") or a.get("text"))
    if action == "run_terminal_command":
        a.setdefault("command", a.get("cmd"))
    return {k: v for k, v in a.items() if v is not None}


# ----------------------------------------------------------------------------- public API
def request(action: str, args: Optional[Dict[str, Any]] = None, *, requested_by: str = "model",
            reason: str = "") -> Dict[str, Any]:
    """Create (or return the identical existing) pending request. Never executes anything."""
    args = dict(args or {})
    try:
        norm, prev = preview(action, args)
    except Refused as e:
        audit("refused_request", action=action, requested_by=requested_by, reason=str(e))
        return {"ok": False, "status": "refused", "action": action, "error": str(e), "executed": False}
    rid = "apr-" + _sha({"action": action, "args": norm, "preview": prev})[:16]
    data = _load()
    item = next((i for i in data["items"] if i.get("id") == rid), None)
    if item is None:
        item = {"id": rid, "action": f"gate:{action}", "status": "pending",
                "payload": {"gate": action, "args": norm, "preview": prev, "preview_sha": _sha(prev),
                            "workspace": str(workspace()), "requested_by": requested_by, "reason": reason[:500],
                            "created_at": round(time.time(), 3)}}
        data["items"].append(item)
        _save(data)
        audit("requested", id=rid, action=action, requested_by=requested_by)
    return {"ok": True, "status": item["status"], "approval_id": rid, "action": action, "preview": prev,
            "executed": bool(item.get("executed")),
            "note": "pending human approval in the approval UI; nothing has run"}


def get(req_id: str) -> Optional[Dict[str, Any]]:
    return next((i for i in _load()["items"] if i.get("id") == req_id), None)


def pending() -> List[Dict[str, Any]]:
    return [i for i in _load()["items"] if str(i.get("action", "")).startswith("gate:") and i.get("status") == "pending"]


def set_status(req_id: str, status: str, *, by: str) -> bool:
    """Human decision (approval UI / CLI). Models must never call this."""
    if status not in ("approved", "rejected"):
        raise ValueError("status must be approved or rejected")
    data = _load()
    for it in data["items"]:
        if it.get("id") == req_id and it.get("status") == "pending":
            it["status"] = status
            it["decided_by"] = by
            it["decided_at"] = round(time.time(), 3)
            _save(data)
            audit(status, id=req_id, by=by)
            return True
    return False


def _run_edit(norm: Dict[str, Any], prev: Dict[str, Any]) -> Dict[str, Any]:
    path = resolve_in_workspace(norm["file_path"])
    raw = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    if hashlib.sha256(raw.encode()).hexdigest() != prev.get("file_sha256"):
        raise Refused("stale: file changed since the request; re-request")
    if "content" in norm:
        updated = norm["content"]
    else:
        updated = raw.replace(norm["old_string"], norm["new_string"]) if norm.get("replace_all") else \
            raw.replace(norm["old_string"], norm["new_string"], 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding="utf-8")
    return {"ok": True, "file": norm["file_path"], "bytes": len(updated.encode())}


def _run_command(norm: Dict[str, Any], prev: Dict[str, Any]) -> Dict[str, Any]:
    cwd = resolve_in_workspace(norm["cwd"]) if norm.get("cwd") not in (None, "", ".") else workspace()
    t0 = time.time()
    try:
        cp = subprocess.run(prev["argv"], cwd=str(cwd), capture_output=True, text=True, timeout=int(norm["timeout"]))
        return {"ok": cp.returncode == 0, "exit_code": cp.returncode, "stdout": cp.stdout[-8000:],
                "stderr": cp.stderr[-4000:], "duration_ms": int((time.time() - t0) * 1000)}
    except subprocess.TimeoutExpired:
        return {"ok": False, "timed_out": True, "duration_ms": int((time.time() - t0) * 1000)}


def _run_tool(action: str, norm: Dict[str, Any]) -> Dict[str, Any]:
    if action == "auto_wire":
        from abilities import auto_wire

        return {"ok": True, "result": auto_wire.main()}
    if action.startswith("self_heal"):
        from realai.core import self_heal

        fn = {"self_heal_promote": self_heal._promote_impl, "self_heal_curated_promote": self_heal._curated_promote_impl,
              "self_heal_deep_promote": self_heal._deep_promote_impl}[action]
        kw = {"force": bool(norm.get("force"))} if action == "self_heal_curated_promote" else {}
        return fn(apply=True, **kw)
    try:
        mod = __import__(f"realai.server.tools.{action}_tool", fromlist=["run"])
    except ImportError:
        mod = __import__(f"realai.plugins.tools.{action}_tool", fromlist=["run"])
    return mod.run(dict(norm))


def execute(req_id: str, *, executor: str = "human") -> Dict[str, Any]:
    """Run an APPROVED request once. Everything else is refused."""
    item = get(req_id)
    if not item or not str(item.get("action", "")).startswith("gate:"):
        audit("refused_execute", id=req_id, reason="not_found")
        return {"ok": False, "error": "approval request not found"}
    if item.get("executed") or item.get("status") == "executed":
        audit("refused_execute", id=req_id, reason="already_executed")
        return {"ok": False, "error": "already executed"}
    if item.get("status") != "approved":
        audit("refused_execute", id=req_id, reason=f"status={item.get('status')}")
        return {"ok": False, "error": f"not approved (status={item.get('status')})"}
    pl = item["payload"]
    action, norm, prev = pl["gate"], pl["args"], pl["preview"]
    try:
        if _sha(prev) != pl.get("preview_sha"):
            raise Refused("preview hash mismatch")
        _money_check(action, norm)
        if action in ("search_replace", "write_file"):
            res = _run_edit(norm, prev)
        elif action == "run_terminal_command":
            res = _run_command(norm, prev)
        elif action == "trade_execute":
            res = _run_trade(req_id, item, norm, prev)
        elif action == "run_script":
            from realai.bot.live_exec import run_script

            res = run_script(language=norm["language"], code=norm["code"], filename=norm["filename"] or None,
                             argv=norm["argv"] or None)
        else:
            res = _run_tool(action, norm)
    except Refused as e:
        audit("refused_execute", id=req_id, reason=str(e))
        return {"ok": False, "error": str(e)}
    except Exception as e:
        res = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    data = _load()
    for it in data["items"]:
        if it.get("id") == req_id:
            it.update(status="executed", executed=True, executed_by=executor, executed_at=round(time.time(), 3),
                      result={k: (v[:2000] if isinstance(v, str) else v) for k, v in (res or {}).items()})
    _save(data)
    audit("executed", id=req_id, action=action, executor=executor, ok=bool((res or {}).get("ok")))
    return {"ok": bool((res or {}).get("ok")), "approval_id": req_id, "action": action, "result": res}


def run_if_approved(action: str, args: Dict[str, Any], *, requested_by: str = "model") -> Dict[str, Any]:
    """Tool-call entry point: with an approved ``approval_id`` execute it; otherwise create/return the request."""
    aid = str((args or {}).get("approval_id") or "").strip()
    if aid:
        it = get(aid)
        if it and it.get("status") == "approved" and (it.get("payload") or {}).get("gate") == action:
            return execute(aid, executor=f"{requested_by}:approved")
        return {"ok": False, "status": (it or {}).get("status", "unknown"), "approval_id": aid, "executed": False,
                "error": "approval_id is not approved for this action"}
    return request(action, {k: v for k, v in (args or {}).items() if k not in ("approved", "approval_id")},
                   requested_by=requested_by)


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="python -m realai.core.approval_gate")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    for c in ("show", "approve", "reject", "execute"):
        sub.add_parser(c).add_argument("id")
    a = ap.parse_args(argv)
    if a.cmd == "list":
        for it in pending():
            print(it["id"], it["payload"]["gate"], it["payload"].get("requested_by"), it["payload"].get("reason", "")[:60])
        return 0
    it = get(a.id)
    if not it:
        print("not found")
        return 1
    if a.cmd == "show":
        print(json.dumps(it, indent=2)[:20000])
        return 0
    if a.cmd in ("approve", "reject"):
        pv = it["payload"]["preview"]
        print(pv.get("diff") or " ".join(pv.get("argv") or []) or json.dumps(pv, indent=2)[:4000])
        if not sys.stdin.isatty() or input(f"Type the id to {a.cmd}: ").strip() != a.id:
            print("not confirmed")
            return 2
        return 0 if set_status(a.id, "approved" if a.cmd == "approve" else "rejected", by=os.environ.get("USERNAME") or
                               os.environ.get("USER") or "human-cli") else 1
    print(json.dumps(execute(a.id, executor="human-cli"), indent=2, default=str)[:20000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
