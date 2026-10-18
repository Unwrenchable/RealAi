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


def tool_subset(right: List[str], key: str, k: int = 4) -> List[str]:
    """The right tool(s) + seeded distractors, so the model learns to choose (keeps rows short)."""
    from realai.hive_tools import SPECS

    rng = random.Random(_h(key))
    others = [n for n in SPECS if n not in right]
    rng.shuffle(others)
    names = list(dict.fromkeys(right)) + others[: max(0, k - len(set(right)))]
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
        msgs.append({"role": "tool", "name": c["name"], "content": tool_json(c["result"])})
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


# money/trade requests: RealAI never moves funds (money paths are locked); offer the read-only tools instead
_MONEY_ASKS = ["Send {n} SOL from my wallet to my friend right now.", "Transfer {n} USDC to {who}'s wallet.",
               "Release the league payouts to {a} and {b} now.", "Pay out the tournament winnings to {a}.",
               "Send {n} SOL to my other wallet right now.", "Swap {n} SOL for USDC for me.",
               "Buy {n} SOL worth of BONK on my account.", "Tip {who} {n} SOL from the RackUp treasury.",
               "Withdraw {n} USDC from the league pot to my wallet.", "Approve and send the payout to {a} immediately."]
_MONEY_ANSWERS = [
    "I can't do that: RealAI never sends, transfers, trades or releases money. Those paths are locked, and no approval "
    "unlocks them from chat. I can check things read-only instead, for example audit the payouts against the standings "
    "with payout_check or look up a balance with solana_read.",
    "I won't move funds. Sending, swapping or paying out is locked in RealAI, by design. If you want, I can verify the "
    "amounts first (payout_check for league payouts, solana_read for a read-only wallet lookup). The transfer itself has "
    "to be done by you in your own wallet.",
    "I cannot send or release money. RealAI's money paths are locked and read-only, and there is no approval request for "
    "this. I can audit it (payout_check) or show balances (solana_read), but the payment has to come from you."]


def _safety_rows(spec, ctx) -> Iterator[Row]:
    """Refusals for money/trade requests: no tool call, read-only alternatives named."""
    from realai.hive_tools import specs

    names, amounts, who = [("Ana", "Ben"), ("Cole", "Dee"), ("Eli", "Faye")], [0.5, 2, 5, 25], ["Sam", "Jo", "Kai"]
    for i, tmpl in enumerate(_MONEY_ASKS):
        for j in range(3):
            a, b = names[(i + j) % 3]
            q = tmpl.format(n=amounts[(i + j) % 4], who=who[(i * 2 + j) % 3], a=a, b=b)
            key = f"safety{i}-{j}"
            yield {"messages": [{"role": "system", "content": TOOL_SYSTEM}, {"role": "user", "content": q},
                                {"role": "assistant", "content": _MONEY_ANSWERS[(i + j) % len(_MONEY_ANSWERS)]}],
                   "tools": specs(tool_subset(["payout_check", "solana_read", "request_approval"], key)),
                   "meta": {"kind": "safety_refusal", "rule": "money_locked"}}


TOOL_KINDS = {"chess": _chess_rows, "pyramid": _pyramid_rows, "rating": _rating_rows, "shots": _shot_rows,
              "device": _device_rows, "math": _math_rows, "data": _data_rows, "abilities": _ability_rows, "agents": _agent_rows,
              "league": _league_rows, "safety": _safety_rows}


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
            yield {"messages": r["messages"], "tools": r.get("tools"),
                   "meta": {"kind": "tool_call" if r.get("tools") else "plain", "tool": r.get("tool"), "origin": r.get("origin"),
                            "teacher": teacher, "file": path.name}}
