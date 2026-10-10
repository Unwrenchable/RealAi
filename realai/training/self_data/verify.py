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
_FAIL = re.compile(r"\b(fail|failed|error|couldn't|could not|unable|not found|unavailable|disabled|no match)\b", re.I)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).replace("→", "->").replace("\u2014", "-")).strip().lower()


def _nums(s: str) -> List[str]:
    out = []
    for n in _NUM.findall(s or ""):
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
    bad = [n for n in _nums(_strip_markers(ans)) if n not in have]
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
            if r["handoff"]["agent"] not in ans:
                reasons.append("agent_not_named")
        elif name == "ability_lookup":
            top = (r.get("matches") or [{}])[0]
            if top.get("id") and top["id"] not in ans:
                reasons.append("ability_not_named")
            elif top.get("status") and top["status"] not in ans and top["status"].lower() not in ans.lower():
                reasons.append("ability_status_missing")
    if not reasons and judge is not None:
        try:
            if not judge(question=question, answer=ans, tool_output=blob):
                reasons.append("llm_judge_rejected")
        except Exception as exc:
            reasons.append(f"judge_error:{type(exc).__name__}")
    return (not reasons), reasons


def llm_judge(chat) -> Callable[..., bool]:
    """Optional judge on any chat function (tools=None). Answers YES only if every fact is in the tool output."""
    def judge(question: str, answer: str, tool_output: str) -> bool:
        msg = chat([{"role": "system", "content": "You check answers against tool output. Reply YES or NO only."},
                    {"role": "user", "content": f"Question: {question}\nTool output: {tool_output[:2500]}\nAnswer: {answer}\n"
                                                "Is every factual claim in the answer supported by the tool output?"}], None)
        return str(msg.get("content") or "").strip().upper().startswith("YES")

    return judge
