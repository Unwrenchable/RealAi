"""Filter v2 (in-repo port of the round-2 30B filter) + repo_search extension.

A self_data row is dropped when:
  failed_tool                 its last tool result is ok:false (unless it is a refusal the verifier accepted)
  <ability>_keys / _<field>   a rackup_invoke payload uses keys/values the ability does not read (rating_convert with
                              {from,to,rating} silently returns the default estimate)
  repo_search_ungrounded_path the answer cites a file path that no repo_search output (or the question) contains
  repo_search_secret          the answer or tool output carries a secret pattern or a redaction marker in the answer
  repo_search_excluded_repo   repo_search was pointed at an excluded / non-searchable repo and the answer is not a refusal
  repo_search_stale           (--recompute) repo_search on the current mirror no longer gives the same result
  money_approval_filed        request_approval was FILED (pending) for a money command OTHER than a structured
                              trade_execute card (raw buy/swap/deploy/charge/wallet commands, scripts): the only trade path is
                              trade_propose -> request_approval(trade_execute)
  trade_preview_incomplete    a pending trade_execute card without a complete CLI preview (kind/hash/amount/usd/slippage/
                              min-out/caps/wallet), without a matching trade_propose, or filed for a proposal with problems
  trade_executed_claim        the answer says a trade happened (bought/swapped/executed/filled) or never says PENDING
  trade_overrefused           an in-cap, safety-passing proposal (no problems) answered with a refusal and no card filed
  session_preview_incomplete  a pending trade_session card without a complete gate preview, or answered without PENDING /
                              with a claim that it already traded or is already running (-> trade_executed_claim)
  trade_exit_overrefused      a question about the AI closing / reducing its OWN position (exits are exempt from the trade,
                              spend and loss caps and need no card) answered with a refusal; sends to another address stay refused
  trade_session_overrefused   a request to let the AI trade on its own answered with a refusal instead of filing
                              request_approval(trade_session) (refusals stay only for the locked list)

``filter_files(..., write=False)`` only reports. With write=True each file is rewritten in place after its raw is kept
next to it (``.jsonl.raw``, or ``.jsonl.pre-v3`` when a raw already exists) and, if given, copied to ``archive``.
"""
from __future__ import annotations

import glob
import json
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

NEED = {"rating_convert": {"from_system", "from_value"}, "pyramid_rules": {"table_size", "skill_level"}}
ALLOWED = {"rating_convert": {"from_system", "from_value"},
           "pyramid_rules": {"table_size", "skill_level", "my_score", "opp_score"},
           "league_validate": {"my_score", "opp_score", "opponent_id", "discipline", "won"}}
VALUES = {"table_size": {"7ft", "9ft"}, "skill_level": {"beginner", "intermediate", "advanced", "pro"},
          "from_system": {"apa", "fargo", "tap", "bca"}}
MONEY_CMD = re.compile(r"\b(buy|sell|swap|trade|snipe|scalp|bridge|mint|airdrop|withdraw|deposit|charge|payout|pay out|transfer|"
                       r"send\s+\d|wallet|keypair|private key|seed phrase|mnemonic|mainnet|--network\s+main|stripe|"
                       r"scalper|dex_trader|sol_dex|evm_dex|multi_wallet)\b", re.I)
_REFUSAL = re.compile(r"can't|cannot|won't|not able|not allowed|blocked|refus|isn't in|not in the|never|don't", re.I)


_MARK = re.compile(r"<redacted:\w+>")
# [ai-auto] stricter refusal test for the AI auto-trading rules: the answer OPENS with a refusal (a "never goes to another
# address" clause inside an allowed answer is not a refusal)
_OPEN_REFUSAL = re.compile(r"^\W*(?:no[,.]|sorry|i (?:won't|will not|can't|cannot|am not able|'m not able|am unable)|that(?:'s| is) not (?:allowed|possible)|"
                           r"(?:exits?|selling|that) (?:is|are)n't allowed|not allowed|refus)", re.I)
_AI_EXIT_Q = re.compile(r"\b(?:exit|close|sell|unwind|dump|get out|bail|take profit|stop[- ]?loss|flatten|trim|reduce)\b", re.I)
_AI_POS_Q = re.compile(r"\b(?:ai|bot|auto|session)\b.{0,60}\bposition|\bposition.{0,60}\b(?:ai|bot)\b|\bthe ai\b|\bai(?:'s)? (?:trade|bag|buy)", re.I)
_FOREIGN_Q = re.compile(r"\b(?:send|transfer|pay|withdraw|forward)\b|\bto (?:my |another |a )?(?:other |different |fresh )?(?:wallet|address)\b|[1-9A-HJ-NP-Za-km-z]{32,44}", re.I)
_AUTO_Q = re.compile(r"\b(?:on its own|by itself|without asking|auto[- ]?trad\w*|autonomous\w*|ai mode|live-auto|let (?:the )?(?:ai|bot) trade|trade_session|trading session)\b", re.I)
_LOCKED_Q = re.compile(r"\b(?:private key|seed phrase|mnemonic|keypair|kill(?: switch|[- ]file| flag)?|unkill|raise|bump|increase|ignore|bypass|skip|split|"
                       r"scalper|dex_trader|sol_dex|evm_dex|multi_wallet|fizzswap|cookbook|mainnet|bridge|deploy|mint)\b", re.I)


def _guard_refusal(c: Dict[str, Any]) -> bool:
    """A failed call that is the guard working (allowlist / blocked path / money refusal), answered with a refusal."""
    r = c["result"] or {}
    if c["name"] == "repo_search":
        return bool(re.search(r"allowlist|blocked|escapes|relative to the repo", str(r.get("error", ""))))
    if c["name"] == "trade_propose":  # over a cap / failed safety: the proposal's problems ARE the guard working
        return bool(r.get("problems")) and not r.get("error")
    return c["name"] == "request_approval" and r.get("status") == "refused" and r.get("executed") is False


def _args(c: Dict[str, Any]) -> Dict[str, Any]:
    a = (c.get("function") or {}).get("arguments", c.get("arguments"))
    if isinstance(a, str):
        try:
            a = json.loads(a)
        except ValueError:
            return {}
    return a if isinstance(a, dict) else {}


def calls_of(msgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """[{name, arguments, result}] from a transcript (tool_calls followed by role=tool messages, in order)."""
    out: List[Dict[str, Any]] = []
    pending: List[Dict[str, Any]] = []
    for m in msgs:
        for c in m.get("tool_calls") or []:
            pending.append({"name": (c.get("function") or {}).get("name") or c.get("name"), "arguments": _args(c), "result": None})
        if m.get("role") == "tool" and pending:
            c = pending.pop(0)
            try:
                c["result"] = json.loads(m.get("content") or "{}")
            except ValueError:
                c["result"] = {"_unparsed": m.get("content")}
            out.append(c)
    return out


def bad_payload(calls: List[Dict[str, Any]]) -> Optional[str]:
    for c in calls:
        if c["name"] != "rackup_invoke":
            continue
        a = c["arguments"]
        ab, pl = a.get("ability"), a.get("payload") or {}
        if ab in ALLOWED:
            keys = set(pl)
            if not NEED.get(ab, set()) <= keys or not keys <= ALLOWED[ab]:
                return f"{ab}_keys"
            for k, ok in VALUES.items():
                if k in pl and str(pl[k]).lower() not in ok:
                    return f"{ab}_{k}"
    return None


def reject_reason(row: Dict[str, Any], recompute: bool = False) -> Optional[str]:
    from realai.hive_tools import repo_search as R

    msgs = row.get("messages") or []
    calls = calls_of(msgs)
    ans = next((str(m.get("content") or "") for m in reversed(msgs) if m.get("role") == "assistant" and not m.get("tool_calls")), "")
    question = " ".join(str(m.get("content") or "") for m in msgs if m.get("role") == "user")
    refusal = bool(_REFUSAL.search(ans))
    last = calls[-1] if calls else None
    if last and isinstance(last["result"], dict) and last["result"].get("ok") is False and not (refusal and _guard_refusal(last)):
        return "failed_tool"
    why = bad_payload(calls)
    if why:
        return why
    for c in calls:
        if c["name"] == "request_approval" and (c["result"] or {}).get("status") == "pending":
            if c["arguments"].get("action") == "trade_execute":
                why = trade_card_problem(calls, c, ans)
                if why:
                    return why
            elif c["arguments"].get("action") == "trade_session":
                why = session_card_problem(c, ans)
                if why:
                    return why
            elif MONEY_CMD.search(json.dumps(c["arguments"], ensure_ascii=False)) or MONEY_CMD.search(question):
                return "money_approval_filed"
    props = [c for c in calls if c["name"] == "trade_propose" and isinstance(c["result"], dict)]
    if (props and props[-1]["result"].get("ok") and not props[-1]["result"].get("problems") and refusal
            and not any(c["name"] == "request_approval" for c in calls)):
        return "trade_overrefused"
    opens_refusal = bool(_OPEN_REFUSAL.search(ans.strip()))
    if opens_refusal and not _FOREIGN_Q.search(question) and not _LOCKED_Q.search(question):
        if _AI_EXIT_Q.search(question) and _AI_POS_Q.search(question):
            return "trade_exit_overrefused"
        filed = any(c["name"] == "request_approval" and c["arguments"].get("action") == "trade_session" for c in calls)
        if _AUTO_Q.search(question) and not filed:
            return "trade_session_overrefused"
    rs = [c for c in calls if c["name"] == "repo_search"]
    if rs:
        for c in rs:
            repo = str(c["arguments"].get("repo") or "")
            if repo and (R.resolve_repo(repo) is None or not R.searchable(R.resolve_repo(repo) or "")) and not refusal:
                return "repo_search_excluded_repo"
        out_blob = _MARK.sub("", json.dumps([c["result"] for c in rs], ensure_ascii=False))
        if R.find_secret_types(_MARK.sub("", ans)) or "<redacted" in ans.lower() or R.find_secret_types(out_blob):
            return "repo_search_secret"
        ok_results = [c["result"] for c in rs if isinstance(c["result"], dict) and c["result"].get("ok")]
        if ok_results and R.ungrounded_citations(ans, ok_results, question):
            return "repo_search_ungrounded_path"
        if recompute:
            from realai import hive_tools

            for c in rs:
                again = hive_tools.execute("repo_search", c["arguments"], offline=True)
                if json.dumps(again, sort_keys=True) != json.dumps(c["result"], sort_keys=True):
                    return "repo_search_stale"
    return None


def session_card_problem(c: Dict[str, Any], ans: str) -> Optional[str]:
    from .verify import session_check

    bad = session_check(c, ans)
    if not bad:
        return None
    return "trade_executed_claim" if any(b in ("trade_executed_claim", "trade_not_called_pending") for b in bad) else "session_preview_incomplete"


def trade_card_problem(calls: List[Dict[str, Any]], c: Dict[str, Any], ans: str) -> Optional[str]:
    from .verify import trade_check

    bad = trade_check([x for x in calls if isinstance(x["result"], dict) and x["result"].get("ok")], c, ans)
    if not bad:
        return None
    return "trade_executed_claim" if any(b in ("trade_executed_claim", "trade_not_called_pending") for b in bad) else "trade_preview_incomplete"


def filter_rows(rows: List[Dict[str, Any]], recompute: bool = False) -> (List[Dict[str, Any]], Counter):
    keep, stats = [], Counter()
    for r in rows:
        why = reject_reason(r, recompute=recompute)
        stats[f"{r.get('tool')}:{why or 'kept'}"] += 1
        if not why:
            keep.append(r)
    return keep, stats


def filter_files(paths: List[str], teacher_prefix: str = "", archive: Optional[str] = None, recompute: bool = False,
                 write: bool = False) -> Dict[str, Any]:
    files = sorted({Path(p) for raw in paths for p in (glob.glob(raw) or [raw]) if Path(p).is_file()})
    report: Dict[str, Any] = {"write": write, "files": {}, "reasons": {}}
    total = Counter()
    for p in files:
        rows = [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if not rows or (teacher_prefix and not str(rows[0].get("teacher", "")).startswith(teacher_prefix)):
            continue
        keep, stats = filter_rows(rows, recompute=recompute)
        total.update(stats)
        report["files"][p.name] = {"raw": len(rows), "kept": len(keep)}
        if write and len(keep) != len(rows):
            if archive:
                Path(archive).mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, Path(archive) / p.name)
            raw = p.with_suffix(".jsonl.raw")
            if raw.exists():
                raw = p.with_suffix(".jsonl.pre-v3")
            if raw.exists():
                raise SystemExit(f"refused: {raw} exists; move it to the archive first (no overwrite)")
            p.rename(raw)
            p.write_bytes("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in keep).encode("utf-8"))
    report["reasons"] = dict(sorted(total.items()))
    return report
