"""Tool-call SFT sources (Qwen2.5 native tool calling) + self-knowledge + hive self-play ingestion.

Factual rows are routed, not memorised: user -> assistant <tool_call> -> REAL tool output (executed
here, offline, read-only via realai.hive_tools) -> answer that only restates the tool output.
Rows carry ``tools`` (the tool specs shown to the model: the right tool + seeded distractors).
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .adapters import Row, _resolve, adapter

TOOL_SYSTEM = ("You are RealAI, a local hive mind. You do not answer facts from memory: route to the right tool, "
               "ability or agent, then answer only from what it returns. If a tool fails, say so.")


def _h(s: str) -> int:
    return int(hashlib.sha1(s.encode()).hexdigest()[:8], 16)


# Look-alike tools the model confuses when it sees the full live catalog (spotcheck 2026-10-18: pyramid -> hall_context,
# rating_convert/league -> rating_update_preview, agents -> web_search/tool_registry_lookup, hive role -> route_to_agent).
# Rows show these as distractors first, so a 4-tool row still teaches the hard choice.
CONFUSABLE: Dict[str, List[str]] = {
    "rackup_invoke": ["hall_context", "rating_update_preview", "rating_intel", "game_rules", "payout_check", "tool_registry_lookup"],
    "hall_context": ["rackup_invoke", "game_rules"],
    "game_rules": ["rackup_invoke", "hall_context"],
    "rating_update_preview": ["rackup_invoke", "rating_intel"],
    "rating_intel": ["rating_update_preview", "rackup_invoke"],
    "route_to_agent": ["list_agents", "web_search", "tool_registry_lookup", "hive_routes_status", "agent_pipeline_plan"],
    "list_agents": ["route_to_agent", "web_search", "tool_registry_lookup", "plugin_lookup"],
    "ability_lookup": ["rackup_invoke", "tool_registry_lookup", "module_lookup", "plugin_lookup"],
    "tool_registry_lookup": ["ability_lookup", "rackup_invoke", "plugin_registry_list"],
    "hive_routes_status": ["route_to_agent", "agent_pipeline_plan", "organs_hive_status"],
    "agent_pipeline_plan": ["hive_routes_status", "route_to_agent"],
    "device_profile": ["hive_routes_status", "self_heal_status", "web_search"],
    "payout_check": ["rackup_invoke", "solana_read", "request_approval"],
    "approval_status": ["request_approval", "self_heal_status"],
    "request_approval": ["approval_status", "solana_read", "repo_search"],
    "solana_read": ["payout_check", "request_approval"],
    "shot_lookup": ["coach_drill", "game_rules"],
    "coach_drill": ["shot_lookup", "matchmaking_suggest"],
    "math_solver": ["data_analysis"],
    "data_analysis": ["math_solver"],
    "memory_search": ["memory_stats", "repo_search"],
    "memory_stats": ["memory_search"],
    "plugin_lookup": ["plugin_registry_list", "module_lookup", "repo_search"],
    "plugin_registry_list": ["plugin_lookup"],
    "module_lookup": ["plugin_lookup", "ability_lookup", "repo_search"],
    # tool 32 (2026-10-19): code questions about Travis's other repos vs RealAI self-knowledge / memory / web / edits
    "repo_search": ["module_lookup", "plugin_lookup", "memory_search", "web_search", "request_approval", "list_agents"],
}


def tool_subset(right: List[str], key: str, k: int = 4, hard: int = 2) -> List[str]:
    """The right tool(s) + seeded distractors, so the model learns to choose (keeps rows short).
    Up to `hard` distractors come from the right tools' look-alikes (CONFUSABLE), the rest are random."""
    from realai.hive_tools import SPECS

    rng = random.Random(_h(key))
    right = [n for n in dict.fromkeys(right)]
    slots = max(0, k - len(right))
    near = [n for r in right for n in CONFUSABLE.get(r, []) if n in SPECS and n not in right]
    near = list(dict.fromkeys(near))
    rng.shuffle(near)
    picked = near[: min(hard, slots)]
    others = [n for n in SPECS if n not in right and n not in picked]
    rng.shuffle(others)
    names = right + picked + others[: slots - len(picked)]
    rng.shuffle(names)
    return names


def tool_row(question: str, calls: List[Dict[str, Any]], answer: str, *, key: str, meta: Optional[Dict[str, Any]] = None,
             system: str = TOOL_SYSTEM) -> Row:
    """calls: [{"name", "arguments", "result"}] executed in order (one assistant turn per call)."""
    from realai.hive_tools import specs, tool_json

    msgs: List[Dict[str, Any]] = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    for c in calls:
        msgs.append({"role": "assistant", "content": "",
                     "tool_calls": [{"type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}}]})
        msgs.append({"role": "tool", "name": c["name"], "content": tool_json(c["result"], name=c["name"])})
    msgs.append({"role": "assistant", "content": answer})
    return {"messages": msgs, "tools": specs(tool_subset([c["name"] for c in calls], key)),
            "meta": dict(meta or {}, tools_called=[c["name"] for c in calls], kind="tool_call")}


def _call(name: str, args: Dict[str, Any], ctx: Dict[str, Any] | None = None) -> Dict[str, Any]:
    from realai.hive_tools import execute

    return {"name": name, "arguments": args, "result": execute(name, args, offline=True, ctx=ctx)}


# --------------------------------------------------------------------------- answers (only tool facts)
def chess_tool_answer(r: Dict[str, Any]) -> str:
    line = " ".join(r.get("pv_san") or [])
    return (f"{r['side_to_move']} to move. Stockfish (depth {r.get('depth')}) plays {r['best_move_san']} ({r['best_move_uci']}); "
            f"evaluation {r['eval']}." + (f" Engine line: {line}." if line else ""))


CHESS_Q = ["What's the best move here? {fen}", "FEN: {fen}\nWhat should {side} play?",
           "Can you check this position with the engine? {fen}", "Best move and eval for {fen}",
           "I'm stuck in this position ({side} to move): {fen}"]


def _chess_rows(spec, ctx) -> Iterator[Row]:
    """Lichess CC0 positions; engine output comes from the cached Stockfish analysis (or a live engine)."""
    import chess

    depth = int(spec.get("depth", 12))
    keep = ("best_move_san", "best_move_uci", "eval", "pv_san", "side_to_move", "depth", "engine")
    for path in _resolve(spec.get("chess_paths", []), ctx["roots"]):
        cache_p = path.with_name(path.stem + f".stockfish_d{depth}.jsonl")
        cache = {}
        if cache_p.is_file():
            for line in cache_p.read_text(encoding="utf-8").splitlines():
                a = json.loads(line)
                cache[a["fen"]] = a
        with path.open(encoding="utf-8") as f:
            for n, row in enumerate(csv.DictReader(f)):
                if n >= int(spec.get("chess_limit", 600)):
                    break
                b = chess.Board(row["FEN"])
                b.push_uci(row["Moves"].split()[0])
                fen = b.fen()
                a = cache.get(fen)
                if a is None:
                    c = _call("chess_engine", {"fen": fen, "depth": depth})
                    if not c["result"].get("ok"):
                        continue
                    res = c["result"]
                else:
                    res = {"ok": True, **{k: a[k] for k in keep if k in a}}
                args = {"fen": fen} if depth == 12 else {"fen": fen, "depth": depth}
                q = CHESS_Q[_h(fen) % len(CHESS_Q)].format(fen=fen, side=res["side_to_move"])
                yield tool_row(q, [{"name": "chess_engine", "arguments": args, "result": res}], chess_tool_answer(res),
                               key=fen, meta={"puzzle": row.get("PuzzleId")})


def _pyramid_rows(spec, ctx) -> Iterator[Row]:
    qs = ["How many points do I need to win RackUp Pyramid as {a} {sk} on a {t} table?",
          "Pyramid, {t} table, {sk} level: what's the race and is call-shot on?",
          "What are the RackUp Pyramid rules for a {sk} player on {t}?"]
    for t in ("7ft", "9ft"):
        for sk in ("beginner", "intermediate", "advanced", "pro"):
            for i, q in enumerate(qs):
                c = _call("rackup_invoke", {"ability": "pyramid_rules", "payload": {"table_size": t, "skill_level": sk}})
                cfg = (c["result"].get("result") or {}).get("config") or {}
                if not cfg:
                    continue
                ans = (f"Per pyramid_rules: {t} table uses a {cfg['rack_size']}-ball rack; {sk} plays first to {cfg['points_to_win']} points; "
                       f"call-shot: {cfg['call_shot']}; rating weight {cfg['rating_weight']}x; the 1-ball is worth {cfg.get('one_ball_value')}.")
                yield tool_row(q.format(t=t, sk=sk, a="an" if sk[0] in "aeiou" else "a"), [c], ans, key=f"pyr{t}{sk}{i}",
                               meta={"rule": "pyramid"})
            for my, opp in ((10, 20), (30, 12)):
                c = _call("rackup_invoke", {"ability": "pyramid_rules", "payload": {"table_size": t, "skill_level": sk, "my_score": my, "opp_score": opp}})
                race = (c["result"].get("result") or {}).get("race")
                if race:
                    yield tool_row(f"Pyramid {t}, {sk}: I'm on {my}, opponent on {opp}. Where do we stand?", [c],
                                   "From pyramid_rules: " + json.dumps(race, ensure_ascii=False), key=f"race{t}{sk}{my}",
                                   meta={"rule": "pyramid_race"})


def _rating_rows(spec, ctx) -> Iterator[Row]:
    for sysname, vals in (("apa", [2, 3, 4, 5, 6, 7]), ("fargo", [350, 450, 520, 600, 680, 750]), ("tap", [3, 5, 7])):
        for v in vals:
            c = _call("rackup_invoke", {"ability": "rating_convert", "payload": {"from_system": sysname, "from_value": v}})
            r = c["result"].get("result") or {}
            if not r.get("display"):
                continue
            eq = "; ".join(f"{k}: {d}" for k, d in (r.get("equivalents") or {}).items() if d)
            yield tool_row(f"Convert {sysname.upper()} {v} to RackUp/ROC.", [c],
                           f"rating_convert gives {r['display']} (confidence {r.get('confidence')}). Equivalents: {eq}.",
                           key=f"rc{sysname}{v}", meta={"rule": "rating_convert"})


SHOT_Q = ["What's the route for the {n} shot?", "How do I set up the {n}?", "Give me the tip for the {n} shot.",
          "Show me Shot of the Day '{n}'."]


def _shot_rows(spec, ctx) -> Iterator[Row]:
    from realai import hive_tools

    for cat in _resolve(spec.get("catalog_paths", []), ctx["roots"]):
        try:
            from .adapters import load_shot_catalog

            hive_tools.set_shot_catalog(load_shot_catalog(cat))
            break
        except Exception:
            continue
    for s in hive_tools.shots():
        for i, q in enumerate(SHOT_Q):
            if _h(s["id"] + str(i)) % 2 and i:  # ~half the templates per shot
                continue
            c = _call("shot_lookup", {"query": s["name"]})
            r = c["result"]
            if not r.get("ok") or r["id"] != s["id"]:
                continue
            if i == 0:
                ans = f"{r['name']} ({r['id']}): {r['route'] or 'no route line in the catalogue'} Pocket: {r['pocket']}."
            elif i == 1:
                ans = f"{r['name']} setup from the catalogue: " + " ".join(r["setup"]) + (f" {r['route']}" if r["route"] else "")
            elif i == 2:
                ans = f"Catalogue tip for {r['name']}: {r['tip']}"
            else:
                ans = f"{r['name']} ({r['difficulty']}, {r['category']}): {r['what']} {r['route'] or ''}".strip()
            yield tool_row(q.format(n=s["name"]), [c], ans, key=s["id"] + str(i), meta={"shot": s["id"]})


def _device_rows(spec, ctx) -> Iterator[Row]:
    from .adapters_extra import mock_profiles, rec_text, report_text

    qs = ["Here's my hardware:\n{r}\nWhat should RealAI run locally?", "{r}\nWhich model/quant/context and which GPU?"]
    for i, p in enumerate(mock_profiles()):
        c = _call("device_profile", {"profile": p})
        if not c["result"].get("ok"):
            continue
        yield tool_row(qs[i % 2].format(r=report_text(p)), [c], "device_profile recommends: " + rec_text(c["result"]["recommendation"]),
                       key=f"dev{i}", meta={"kind2": "device"})
    c = _call("device_profile", {})
    if c["result"].get("ok"):
        yield tool_row("What model should you run on this machine?", [c], "device_profile recommends: " + rec_text(c["result"]["recommendation"]),
                       key="devlocal", meta={"kind2": "device_local"})


def _math_rows(spec, ctx) -> Iterator[Row]:
    try:
        import sympy  # noqa: F401
    except ImportError:
        return
    rng = random.Random(7)
    probs = []
    for _ in range(int(spec.get("math_n", 40))):
        a, b, c = rng.randint(2, 9), rng.randint(-20, 20), rng.randint(-30, 30)
        probs.append(f"solve {a}*x + {b} = {c} for x")
        probs.append(f"derivative of x**{a} + {b}*x")
        probs.append(f"{a * 17} * {abs(b) + 3} - {abs(c)}")
    for p in probs:
        cl = _call("math_solver", {"problem": p})
        r = cl["result"]
        if not r.get("ok") or r.get("answer") is None:
            continue
        yield tool_row(f"Compute: {p}", [cl], f"math_solver ({r.get('method', 'sympy')}): {r['answer']}." +
                       (" Verified." if r.get("verified") else ""), key="m" + p, meta={"kind2": "math"})


def _data_rows(spec, ctx) -> Iterator[Row]:
    rng = random.Random(11)
    for i in range(int(spec.get("data_n", 25))):
        xs = [rng.randint(1, 120) for _ in range(rng.randint(5, 12))]
        c = _call("data_analysis", {"data": xs})
        r = c["result"]
        if not r.get("ok"):
            continue
        st = r.get("stats") or r.get("summary") or {k: v for k, v in r.items() if k != "ok"}
        yield tool_row(f"Give me stats for these numbers: {', '.join(map(str, xs))}", [c],
                       "data_analysis: " + json.dumps(st, ensure_ascii=False)[:500], key=f"d{i}", meta={"kind2": "data"})


def _ability_rows(spec, ctx) -> Iterator[Row]:
    from realai.hive_tools import abilities

    for a in abilities():
        kw = (a.get("keywords") or [a["name"]])[0]
        c = _call("ability_lookup", {"query": a["name"]})
        m = (c["result"].get("matches") or [None])[0]
        if not m or m["id"] != a["id"]:
            continue
        yield tool_row(f"Can you do {kw}?", [c],
                       f"Yes: ability `{m['id']}` ({m['name']}) is {m['status']}. Call it via {m['live_path']}."
                       if m["status"] == "LIVE" else
                       f"Partly: ability `{m['id']}` ({m['name']}) is {m['status']}, so expect gaps. Path: {m['live_path']}.",
                       key="ab" + a["id"], meta={"ability": a["id"]})


def _agent_task(a: Dict[str, Any]) -> str:
    d = str(a.get("description") or a.get("role") or "").split(". ")[0].rstrip(".")
    return d[:220]


def _agent_rows(spec, ctx) -> Iterator[Row]:
    from realai.hive_tools import agents

    for a in agents():
        task = _agent_task(a)
        if len(task) < 25:
            continue
        q = f"I need help: {task[0].lower() + task[1:]}."
        role = a.get("role") or a["id"]
        if _h(a["id"]) % 3 == 0:  # discover first, then hand off
            c1 = _call("list_agents", {"query": role})
            ids = [x["id"] for x in c1["result"].get("agents") or []]
            if a["id"] not in ids:
                continue
            c2 = _call("route_to_agent", {"agent": a["id"], "task": task})
            calls = [c1, c2]
        else:
            calls = [_call("route_to_agent", {"agent": a["id"], "task": task})]
        if not calls[-1]["result"].get("ok"):
            continue
        yield tool_row(q, calls, f"Routed to `{a['id']}` ({role}); handoff queued. That agent owns this task, I'll relay its result.",
                       key="ag" + a["id"], meta={"agent": a["id"]})


def _league_rows(spec, ctx) -> Iterator[Row]:
    """league_validate through rackup_invoke: answers quote the validator's errors/warnings verbatim."""
    cases = [({}, "Validate this league match submission: I didn't enter any scores yet."),
             ({}, "Can you check my league match entry? I left the score boxes empty."),
             ({"opponent_id": "u7", "discipline": "8-ball"}, "League submission vs player u7 in 8-ball, no score entered yet. Is it valid?"),
             ({"my_score": 7, "opp_score": 5}, "I won 7-5 in league tonight. Validate the submission before I send it."),
             ({"my_score": 7, "opp_score": 5, "opponent_id": "u2", "discipline": "8-ball"}, "Check my league result: 7-5 against u2, 8-ball."),
             ({"my_score": 3, "opp_score": 9, "opponent_id": "u4", "discipline": "9-ball"}, "Validate: lost 3-9 to u4 in 9-ball."),
             ({"my_score": -1, "opp_score": 5, "opponent_id": "u2", "discipline": "9-ball"}, "League entry says -1 to 5 vs u2 (9-ball). Is that OK?"),
             ({"my_score": 5, "opp_score": 5, "opponent_id": "u9", "discipline": "10-ball"}, "Is a 5-5 league result vs u9 in 10-ball valid?"),
             ({"my_score": 6, "opp_score": 2, "discipline": "one pocket"}, "One pocket league match, 6-2, I forgot to pick the opponent. Validate it.")]
    for i, (payload, q) in enumerate(cases):
        c = _call("rackup_invoke", {"ability": "league_validate", "payload": payload})
        r = c["result"].get("result") or {}
        if "valid" not in r:
            continue
        errs, warns = r.get("errors") or [], r.get("warnings") or []
        if r["valid"]:
            ans = "league_validate: the submission is valid" + (f", with warnings: {'; '.join(warns)}." if warns else " with no errors or warnings.")
        else:
            ans = f"league_validate: not valid. Errors: {'; '.join(errs)}." + (f" Warnings: {'; '.join(warns)}." if warns else "") + \
                  " Fix those and validate again before submitting."
        yield tool_row(q, [c], ans, key=f"league{i}", meta={"rule": "league_validate"})


# money/trade/approval requests: RealAI never moves funds or approves for the user. The rows check first with the read-only
# tool the live suite expects (payout_check for payouts, approval_status for "approve it", request_approval for a send,
# which the gate refuses), then refuse; one in three refuses without a tool call.
_SEND_ASKS = [("Send {n} SOL from my wallet to my friend right now.", "send_sol"), ("Transfer {n} USDC to {who}'s wallet.", "transfer_usdc"),
              ("Send {n} SOL to my backup wallet now.", "send_sol"), ("Swap {n} SOL for USDC for me.", "swap_tokens"),
              ("Buy {n} SOL worth of BONK on my account.", "buy_token"), ("Tip {who} {n} SOL from the RackUp treasury.", "send_sol"),
              ("Move {n} SOL into my trading account right away.", "send_sol")]
_PAYOUT_ASKS = ["Release the payouts to {a} and {b} right now.", "Pay out tonight's league winnings to {a} and {b}.",
                "Send the tournament prize money to {a} and {b}.", "Go ahead and release {a}'s and {b}'s payouts.",
                "Withdraw the league pot and pay {a} and {b}."]
_APPROVE_ASKS = ["Approve everything in my approval queue.", "Just approve the pending requests for me.",
                 "Mark all my approval requests as approved.", "Approve the latest write request yourself.",
                 "Can you auto-approve whatever is waiting?"]
_SEND_REFUSE = ["I can't do that: RealAI never sends, transfers, swaps or buys anything. Money paths are locked, and the approval "
                "gate refused this action (not filed). I can look things up read-only (solana_read for a balance, payout_check to audit "
                "payouts); the transfer itself has to come from you, in your own wallet.",
                "I won't move funds. That action is locked in RealAI by design, and request_approval refused it: nothing was filed and no money moved. "
                "If it helps, I can check a balance read-only or audit payouts first."]
_SEND_PLAIN = "I can't send or move money. RealAI's money paths are locked and read-only; no approval unlocks them from chat. " \
              "I can check a balance (solana_read) or audit payouts (payout_check) instead."


def _safety_rows(spec, ctx) -> Iterator[Row]:
    from realai.hive_tools import specs

    names, amounts, who = [("Ana", "Ben"), ("Cole", "Dee"), ("Eli", "Faye")], [0.5, 2, 5, 25], ["Sam", "Jo", "Kai"]
    for i, (tmpl, action) in enumerate(_SEND_ASKS):
        for j in range(3):
            q = tmpl.format(n=amounts[(i + j) % 4], who=who[(i * 2 + j) % 3])
            key = f"safety-send{i}-{j}"
            if j == 2:
                yield {"messages": [{"role": "system", "content": TOOL_SYSTEM}, {"role": "user", "content": q},
                                    {"role": "assistant", "content": _SEND_PLAIN}],
                       "tools": specs(tool_subset(["request_approval", "solana_read", "payout_check"], key)),
                       "meta": {"kind": "safety_refusal", "rule": "money_locked"}}
                continue
            c = _call("request_approval", {"action": action, "reason": q})
            if c["result"].get("executed") or c["result"].get("status") != "refused":
                continue  # only rows where the gate really refused
            yield tool_row(q, [c], _SEND_REFUSE[(i + j) % 2], key=key, meta={"kind": "safety_refusal", "rule": "money_locked"})
    for i, tmpl in enumerate(_PAYOUT_ASKS):
        for j in range(3):
            a, b = names[(i + j) % 3]
            q = tmpl.format(a=a, b=b)
            if j == 2:  # amounts given: audit passes, still no release
                q += f" Standings: {a} 1st, {b} 2nd. Payouts: {a} $120, {b} $60."
                c = _call("payout_check", {"standings": [a, b], "payouts": [{"player": a, "amount": 120}, {"player": b, "amount": 60}]})
                summ = c["result"].get("summary") or "audit done"
                ans = (f"payout_check: {summ} But I can't release payouts: RealAI only audits, it never moves money. RackUp releases "
                       f"payouts after a human signs off.")
            else:
                c = _call("payout_check", {"standings": [a, b], "payouts": []})
                ans = ("I can't release payouts: RealAI only audits them (payout_check), it never pays anyone. RackUp releases payouts "
                       "after a human approves. Send me the final standings and each payout (player, amount) and I'll check they line up.")
            yield tool_row(q, [c], ans, key=f"safety-pay{i}-{j}", meta={"kind": "safety_refusal", "rule": "payout_release"})
    for i, q in enumerate(_APPROVE_ASKS):
        c = _call("approval_status", {})
        r = c["result"]
        n = r.get("total", len(r.get("items") or []))
        ans = (f"I can't approve requests for you: approving happens only in the approval UI, by you. approval_status shows "
               f"{n} pending request{'s' if n != 1 else ''}" + (", so there is nothing waiting." if not n else "; open the approval UI to review them."))
        yield tool_row(q, [c], ans, key=f"safety-appr{i}", meta={"kind": "safety_refusal", "rule": "approve_self"})


def _hive_meta_rows(spec, ctx) -> Iterator[Row]:
    """hive_routes_status (role -> model), tool_registry_lookup (is there a tool + status), ability_lookup (is an ability live)."""
    hr = _call("hive_routes_status", {})
    roles = (hr["result"].get("role_models") or {}) if hr["result"].get("ok") else {}
    qs = ["What model runs the {r} role in the hive?", "Which LLM is assigned to the {r} hive role?", "Hive check: what's the {r} role running on?"]
    for role, model in sorted(roles.items()):
        for i, q in enumerate(qs):
            c = _call("hive_routes_status", {"role": role})
            m = (c["result"].get("role_models") or {}).get(role) or c["result"].get("role_model") or model
            yield tool_row(q.format(r=role), [c], f"hive_routes_status: the {role} role uses `{m}`.", key=f"hr{role}{i}",
                           meta={"rule": "hive_role_model"})
    for i, (term, q) in enumerate([("ledger audit", "Is there a ledger audit tool, and is it live?"),
                                   ("ledger", "What's the status of your ledger tooling?"),
                                   ("payout sanity", "Do you have a payout sanity checker? Status?"),
                                   ("money anomaly", "Is the money anomaly detector available?"),
                                   ("league validate", "Do you have something to validate league submissions, and is it on?"),
                                   ("pyramid rules", "Is there a pyramid rules tool in your registry?"),
                                   ("rating convert", "Do you have a rating conversion tool, what's its status?"),
                                   ("shot", "Which shot tools are registered?")]):
        c = _call("tool_registry_lookup", {"query": term})
        tools = c["result"].get("tools") or []
        if not tools:
            continue
        t = tools[0]
        st = str(t.get("status") or "unknown").lower()
        desc = str(t.get("description") or "").split("]", 1)[-1].strip()[:140]
        yield tool_row(q, [c], f"Yes: `{t['id']}` is {st}. {desc}", key=f"reg{i}", meta={"rule": "registry"})
    from realai.hive_tools import abilities

    for i, ab in enumerate(sorted(abilities(), key=lambda x: x["id"])[:40]):
        name = ab.get("name") or ab["id"].replace("_", " ")
        q = ["Is the {n} ability available right now?", "What's the status of your {n} ability?", "Can I use {n} today?"][i % 3].format(n=name)
        c = _call("ability_lookup", {"query": name})
        m = next((x for x in c["result"].get("matches") or [] if x.get("id") == ab["id"]), None)
        if not m:
            continue
        yield tool_row(q, [c], f"ability_lookup: {m['id']} ({m.get('name', name)}) is {str(m.get('status', '')).upper()}. "
                               f"Call path: {m.get('live_path', 'n/a')}.", key=f"abst{ab['id']}", meta={"rule": "ability_status"})


TOOL_KINDS = {"chess": _chess_rows, "pyramid": _pyramid_rows, "rating": _rating_rows, "shots": _shot_rows,
              "device": _device_rows, "math": _math_rows, "data": _data_rows, "abilities": _ability_rows, "agents": _agent_rows,
              "league": _league_rows, "safety": _safety_rows, "hive_meta": _hive_meta_rows}


@adapter("tool_calls")
def tool_calls_source(spec: Dict[str, Any], ctx: Dict[str, Any]) -> Iterator[Row]:
    for kind in spec.get("kinds", list(TOOL_KINDS)):
        yield from TOOL_KINDS[kind](spec, ctx)


# --------------------------------------------------------------------------- self-knowledge (regenerated every build)
def _plain(q: str, a: str) -> Row:
    return {"messages": [{"role": "system", "content": TOOL_SYSTEM}, {"role": "user", "content": q}, {"role": "assistant", "content": a}],
            "meta": {"kind": "self_knowledge"}}


@adapter("self_knowledge")
def self_knowledge_source(spec: Dict[str, Any], ctx: Dict[str, Any]) -> Iterator[Row]:
    """What RealAI is made of, read from the live catalog/tools/agents/modules at build time (never stale)."""
    from realai.hive_tools import SPECS, abilities, agents

    ab = abilities()
    by_p: Dict[str, List[Dict[str, Any]]] = {}
    for a in ab:
        by_p.setdefault(a.get("pillar", "other"), []).append(a)
    for p, rows in sorted(by_p.items()):
        yield _plain(f"Which of your abilities cover {p.replace('_', ' ')}?",
                     "\n".join(f"- `{a['id']}` ({a['name']}): {a['status']}" for a in rows))
    for a in ab:
        note = a.get("status_note") or ""
        yield _plain(f"What is your `{a['id']}` ability and is it live?",
                     f"`{a['id']}` = {a['name']} (pillar {a.get('pillar')}). Status: {a['status']}. "
                     + (f"{note} " if note else "") + f"Call path: {a.get('live_path')}. Modules: {', '.join(a.get('modules') or []) or 'n/a'}.")
    n = {s: sum(1 for a in ab if a["status"] == s) for s in ("LIVE", "PARTIAL", "STUB")}
    yield _plain("How many abilities do you have, and how many are live?",
                 f"{len(ab)} catalogued abilities: {n['LIVE']} LIVE, {n['PARTIAL']} PARTIAL, {n['STUB']} STUB (from realai/ability_catalog.py).")
    yield _plain("What tools can you call?", "\n".join(f"- {k}: {v['function']['description']}" for k, v in SPECS.items()))
    for k, v in SPECS.items():
        props = v["function"]["parameters"]["properties"]
        req = v["function"]["parameters"].get("required") or []
        yield _plain(f"How do I call your {k} tool?",
                     f"{k}: {v['function']['description']} Arguments: " +
                     ", ".join(f"{p}{' (required)' if p in req else ''}: {d.get('type', 'any')}" for p, d in props.items()) + ".")
    ag = agents()
    if ag:
        divs: Dict[str, int] = {}
        for a in ag:
            divs[a.get("division") or (a.get("tags") or ["general"])[0]] = divs.get(a.get("division") or (a.get("tags") or ["general"])[0], 0) + 1
        yield _plain("How many agents are in your hive?", f"{len(ag)} agents in agents/agentx/agents.json. Largest groups: " +
                     ", ".join(f"{k} ({v})" for k, v in sorted(divs.items(), key=lambda t: -t[1])[:8]) +
                     ". I route tasks to them with list_agents and route_to_agent.")
    root = Path(__file__).resolve().parents[3]
    mods = sorted(p.name for p in (root / "modules").iterdir() if p.is_dir() and not p.name.startswith("_")) if (root / "modules").is_dir() else []
    plugs = sorted(p.name for p in (root / "realai" / "plugins").iterdir() if (p / "__init__.py").is_file()) if (root / "realai" / "plugins").is_dir() else []
    if mods:
        yield _plain("What modules are you built from?", "modules/: " + ", ".join(mods) + ". Plugins (realai/plugins): " + ", ".join(plugs[:40]) + ".")
    yield _plain("How do you get better?",
                 "Through the self-data loop: I write questions per ability, run them through the real tools, keep only answers a "
                 "verifier proves grounded (engine move matches Stockfish, numbers match tool output, routes match the catalogue), "
                 "and the spot-check gate decides promotion. Failures become targeted questions for the next dataset.")
    for q, a in (("Who are you?", "I'm RealAI, a local hive mind running on this PC: the orchestrator on 127.0.0.1:8001 routes work to "
                  "tools, abilities and agents; models run in llama-server on Vulkan (:8080). I answer from tool results, not memory."),
                 ("Are you ChatGPT or Qwen?", "I'm RealAI. My local weights are fine-tuned from open models (Qwen2.5, Apache-2.0), but I run "
                  "locally as the RealAI hive and route facts to my tools.")):
        yield _plain(q, a)


# --------------------------------------------------------------------------- hive self-play (verified rows written by self_data)
@adapter("hive_selfplay")
def hive_selfplay_source(spec: Dict[str, Any], ctx: Dict[str, Any]) -> Iterator[Row]:
    # optional "teachers" / "exclude_teachers": split rows by the model that wrote them (e.g. a separate source
    # for one generator so the mix can cap the rest without dropping its rows)
    only, skip = set(spec.get("teachers") or []), set(spec.get("exclude_teachers") or [])
    # optional "resubset_tools": rebuild each tool row's tool list with the current tool_subset (hard distractors)
    resub = bool(spec.get("resubset_tools"))
    from realai.hive_tools import specs
    for path in _resolve(spec.get("paths", ["{realai}/datasets/_sources/hive_selfplay/*.jsonl"]), ctx["roots"]):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if not r.get("verified"):
                continue
            teacher = r.get("teacher")
            names = {teacher, (teacher or "").split("@")[0]}  # self_data tags "model@base_url"
            if only and not names & only:
                continue
            if names & skip:
                continue
            tools = r.get("tools")
            called = [(c.get("function") or {}).get("name") for m in r["messages"] for c in (m.get("tool_calls") or [])]
            called = [c for c in called if c]
            if resub and tools and called:  # same key as self_data.make_row, current distractor policy
                tools = specs(tool_subset(called, json.dumps(r["messages"][1:2])))
            yield {"messages": r["messages"], "tools": tools,
                   "meta": {"kind": "tool_call" if tools else "plain", "tool": r.get("tool"), "origin": r.get("origin"),
                            "teacher": teacher, "file": path.name}}
