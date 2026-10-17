"""Verifier: keep a row only if the tool succeeded and the final answer is grounded in tool output.

Programmatic checks (no model needed):
  * at least one tool call that returned ok (failed tools: answer must admit the failure),
  * chess: answer names the engine's best move (SAN or UCI) and no other move as "best",
  * numbers: every number in the answer appears in the tool output or the question,
  * shots: a quoted route must match the catalogue route text,
  * agents: the answer names the agent that received the handoff,
  * abilities: the answer's ability id and status match the catalog.
Optional LLM judge (``judge`` callable returning True/False) runs last.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

_NUM = re.compile(r"(?<![A-Za-z0-9_])[-+]?\d+(?:\.\d+)?")
_FAIL = re.compile(r"\b(fail|failed|error|couldn't|could not|can't|cannot|unable|not found|unavailable|disabled|no match|"
                   r"refused|rejected|denied|blocked|not filed|was not (?:filed|approved|executed)|"
                   r"issue|problem|invalid|missing|please provide|need the|need more|there (?:are|is|were) no|no \w+ (?:match|matches|found))\b", re.I)
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).replace("→", "->").replace("\u2014", "-")).strip().lower()


def _nums(s: str) -> List[str]:
    out = []
    for n in _NUM.findall(_THOUSANDS.sub("", s or "")):
        try:
            f = float(n)
        except ValueError:
            continue
        out.append(f"{f:g}")
    return out


_LISTNUM = re.compile(r"(?m)^\s*(?:[#>*-]+\s*)?\d+[.)]\s+")
_MOVENUM = re.compile(r"\b\d+\.(?:\.\.)?\s*(?=[KQRBNO]|[a-h][1-8x])")


def _strip_markers(s: str) -> str:
    """Drop list numbering ("4. ") and chess move numbers ("34. f4", "12...Nf6"): formatting, not claims."""
    return _MOVENUM.sub(" ", _LISTNUM.sub("", s))


def _decimals(tok: str, ans: str) -> int:
    m = re.search(r"(?<![\d.])" + re.escape(tok).replace(r"\.", r"\.") + r"(\.\d+)?", _THOUSANDS.sub("", ans))
    return len(m.group(1)) - 1 if m and m.group(1) else (len(tok.split(".")[1]) if "." in tok else 0)


def _derived(n: str, ans: str, have: set) -> bool:
    """A number is still grounded if it is a tool value rounded to the answer's precision (6.48 for 6.480741),
    a percentage of a 0-1 tool value, or a difference of two tool values (range = max - min)."""
    try:
        x = float(n)
    except ValueError:
        return False
    vals = []
    for h in have:
        try:
            vals.append(float(h))
        except ValueError:
            pass
    d = len(n.split(".")[1]) if "." in n else 0
    tol = 0.5 * 10 ** -d + 1e-9
    if any(abs(v - x) <= tol for v in vals):
        return True
    if any(abs(v * 100 - x) <= tol for v in vals if -1 <= v <= 1):
        return True
    small = vals[:60]
    return any(abs(abs(a - b) - x) <= tol for i, a in enumerate(small) for b in small[i + 1:])


def final_answer(messages: List[Dict[str, Any]]) -> str:
    for m in reversed(messages):
        if m.get("role") == "assistant" and not m.get("tool_calls"):
            return str(m.get("content") or "")
    return ""


def verify(messages: List[Dict[str, Any]], calls: List[Dict[str, Any]], judge: Optional[Callable[..., bool]] = None,
           require_tool: bool = True) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    ans = final_answer(messages)
    question = " ".join(str(m.get("content") or "") for m in messages if m.get("role") == "user")
    if not ans.strip():
        return False, ["empty_answer"]
    if "<tool_call>" in ans:
        return False, ["unparsed_tool_call_in_answer"]
    if not calls:
        return (not require_tool), (["no_tool_call"] if require_tool else [])
    ok_calls = [c for c in calls if (c.get("result") or {}).get("ok")]
    if not ok_calls:
        return (bool(_FAIL.search(ans)), ["all_tools_failed" + ("" if _FAIL.search(ans) else "_but_answer_claims_success")])
    blob = json.dumps([c["result"] for c in ok_calls] + [c.get("arguments") for c in calls], ensure_ascii=False)
    have = set(_nums(blob)) | set(_nums(question)) | {"0", "1", "2", "3"}
    bad = [n for n in _nums(_strip_markers(ans)) if n not in have and not _derived(n, ans, have)]
    if bad:
        reasons.append("ungrounded_numbers:" + ",".join(sorted(set(bad))[:6]))
    for c in ok_calls:
        r, name = c["result"], c.get("name")
        if name == "chess_engine":
            if r["best_move_san"] not in ans and r["best_move_uci"] not in ans:
                reasons.append("chess_best_move_missing")
            sans = set(re.findall(r"\b(?:[KQRBN][a-h]?[1-8]?x?[a-h][1-8]|[a-h]x[a-h][1-8]|O-O(?:-O)?)[+#]?", ans))
            allowed = set(r.get("pv_san") or []) | {r["best_move_san"]} | set(re.findall(r"\S+", question))
            extra = {s for s in sans if s not in allowed and s.rstrip("+#") not in {a.rstrip("+#") for a in allowed}}
            if extra:
                reasons.append("chess_moves_not_from_engine:" + ",".join(sorted(extra)))
        elif name == "shot_lookup":
            if "route" in ans.lower() and r.get("route"):
                rt = _norm(r["route"]).replace("route:", "").strip()
                if rt not in _norm(ans):
                    reasons.append("route_mismatch")
            if r.get("name") and _norm(r["name"]) not in _norm(ans) and r.get("id", "") not in ans:
                reasons.append("shot_not_named")
        elif name == "route_to_agent":
            h = r["handoff"]
            names = {str(h.get("agent") or ""), str(h.get("role") or "")}
            names |= {re.sub(r"[-_]+", " ", n) for n in names}
            if not any(n.strip() and n.lower() in ans.lower() for n in names):  # id or role ("Tax Strategist") counts
                reasons.append("agent_not_named")
        elif name == "ability_lookup":
            # any returned match may be the one the user meant; it must be named (id or name) with its status
            low = ans.lower()
            named = [m for m in r.get("matches") or [] if (m.get("id") and (m["id"].lower() in low or m["id"].replace("_", " ") in low))
                     or (m.get("name") and m["name"].lower() in low)]
            if r.get("matches") and not named:
                reasons.append("ability_not_named")
            elif named and not any(str(m.get("status", "")).lower() in low for m in named if m.get("status")):
                reasons.append("ability_status_missing")
    reasons += recompute_check(ok_calls, ans)
    if not reasons and judge is not None:
        try:
            if not judge(question=question, answer=ans, tool_output=blob):
                reasons.append("llm_judge_rejected")
        except Exception as exc:
            reasons.append(f"judge_error:{type(exc).__name__}")
    return (not reasons), reasons


def recompute_check(ok_calls: List[Dict[str, Any]], ans: str) -> List[str]:
    """Wire-audit tools (and route_to_agent): re-run the SAME executor with the same arguments; the result must be
    identical (deterministic, grounded) and the answer must state the key fact(s) from it."""
    from realai import hive_tools

    out: List[str] = []
    low = _norm(ans)
    for c in ok_calls:
        name = c.get("name")
        if name not in hive_tools.NEW_TOOLS and name != "route_to_agent":
            continue
        args = c.get("arguments") if isinstance(c.get("arguments"), dict) else {}
        if name == "request_approval":
            from realai.hive_tools.approvals import contract_violation

            bad = contract_violation(c.get("result") or {})
            if bad:
                out.append(bad)
                continue
        again = hive_tools.execute(str(name), args, offline=True)
        if json.dumps(again, sort_keys=True, default=str) != json.dumps(c["result"], sort_keys=True, default=str):
            out.append(f"recompute_mismatch:{name}")
            continue
        for group in hive_tools.key_facts(str(name), c["result"], args):
            alts = [g for g in group if g and g != "None"]
            if alts and not any(fact_hit(g, low) for g in alts):
                out.append(f"{name}_fact_missing")
                break
    return out


def fact_hit(fact: Any, low: str) -> bool:
    """One key-fact alternative against a normalised answer.

    str: the fact, or the fact with ``_`` read as spaces, appears; a multi-word snake_case fact
    ("provisional_slipping") also counts when every word appears ("provisional and slipping").
    list/tuple: ALL of its items must hit (e.g. every route name listed instead of the route count)."""
    if isinstance(fact, (list, tuple)):
        return bool(fact) and all(fact_hit(f, low) for f in fact)
    f = _norm(fact)
    if f in low or f.replace("_", " ") in low:
        return True
    words = [w for w in re.split(r"[_\s]+", f) if w]
    return "_" in f and len(words) > 1 and all(re.search(r"\b" + re.escape(w) + r"\b", low) for w in words)


def llm_judge(chat) -> Callable[..., bool]:
    """Optional judge on any chat function (tools=None). Answers YES only if every fact is in the tool output."""
    def judge(question: str, answer: str, tool_output: str) -> bool:
        msg = chat([{"role": "system", "content": "You check answers against tool output. Reply YES or NO only."},
                    {"role": "user", "content": f"Question: {question}\nTool output: {tool_output[:2500]}\nAnswer: {answer}\n"
                                                "Is every factual claim in the answer supported by the tool output?"}], None)
        return str(msg.get("content") or "").strip().upper().startswith("YES")

    return judge
