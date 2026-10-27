"""Question generator + executor: the hive writes its own questions and runs them through the real tools.

  questions  <- local model (default :8080) proposes user requests per tool from the tool's schema + seeds
  execute    <- realai.hive_tools.tool_loop with the same model routing to realai.hive_tools (read-only, offline)
  verify     <- realai.training.self_data.verify (programmatic; optional LLM judge)
  write      -> REALAI_HOME/datasets/_sources/hive_selfplay/selfplay-<stamp>.jsonl (+ rejects-<stamp>.jsonl)
"""
from __future__ import annotations

import csv
import datetime as _dt
import json
import os
import random
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from realai import hive_tools
from realai.hive_tools import tool_loop

from .verify import verify

TARGETS = ("chess_engine", "rackup_invoke", "shot_lookup", "math_solver", "data_analysis", "ability_lookup",
           "list_agents", "route_to_agent", "device_profile") + tuple(hive_tools.NEW_TOOLS) + ("repo_search",)
# teacher-only hints (round 3): the 30B teacher saw rackup_invoke's payload as a free object and guessed keys
# (rating_convert {from,to,rating}, league_validate {player_rating,...}) and routed pyramid / conversion / validation asks
# to hall_context / rating_update_preview, and answered specialist jobs itself instead of route_to_agent. The teacher gets a
# typed payload schema + routing rules; the SAVED row keeps the plain TOOL_SYSTEM and the live specs (the student learns
# the routing and keys from the calls, not from hints it will never see at inference).
RACKUP_PAYLOADS = {
    "pyramid_rules": {"table_size": "7ft|9ft (required)", "skill_level": "beginner|intermediate|advanced|pro (required)",
                      "my_score": "int (optional)", "opp_score": "int (optional)"},
    "rating_convert": {"from_system": "apa|fargo|tap|bca (required)", "from_value": "number (required), e.g. APA SL 5 -> 5, Fargo 520 -> 520"},
    "league_validate": {"my_score": "int", "opp_score": "int", "opponent_id": "string", "discipline": "8-ball|9-ball|10-ball|one pocket",
                        "won": "bool (instead of scores)"},
}
TEACHER_HINTS = (
    "\n\nRouting rules (follow exactly):\n"
    "- Pyramid points / race / call-shot for a table size and skill level -> rackup_invoke ability pyramid_rules "
    "(payload {table_size, skill_level}); NOT hall_context, NOT game_rules.\n"
    "- Converting an APA / Fargo / TAP / BCA rating to the RackUp/ROC scale -> rackup_invoke ability rating_convert "
    "(payload {from_system, from_value}); NOT rating_update_preview (that is only for a new rating after a match).\n"
    "- Checking / validating a league match submission (scores, opponent, discipline; even an empty one) -> rackup_invoke "
    "ability league_validate (payload {my_score, opp_score, opponent_id, discipline}); NOT rating_update_preview.\n"
    "- A job for a specialist (audit, review, draft, design, plan, analyse, build) -> route_to_agent with the exact agent id "
    "(list_agents first if unsure); e.g. security audits -> a security agent, WCAG / screen-reader checks -> accessibility-auditor. "
    "Do not answer the job yourself, do not use web_search or tool_registry_lookup for it, and name the agent in the answer.\n"
    "- Use ONLY the payload keys listed in the rackup_invoke schema.")


TEACHER_PAYLOAD_SCHEMA = {  # explicit types + enums (round-3 sample: a substring type guess made skill_level an integer)
    "table_size": {"type": "string", "enum": ["7ft", "9ft"]},
    "skill_level": {"type": "string", "enum": ["beginner", "intermediate", "advanced", "pro"]},
    "my_score": {"type": "integer"}, "opp_score": {"type": "integer"},
    "from_system": {"type": "string", "enum": ["apa", "fargo", "tap", "bca"]},
    "from_value": {"type": "number", "description": "APA SL 5 -> 5, Fargo 520 -> 520"},
    "opponent_id": {"type": "string", "description": "e.g. p2, p17"},
    "discipline": {"type": "string", "enum": ["8-ball", "9-ball", "10-ball", "one pocket"]},
    "won": {"type": "boolean", "description": "instead of scores"},
}


def teacher_specs(names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Live specs, with rackup_invoke's payload typed per ability (teacher only; rows keep the live specs)."""
    import copy

    out = copy.deepcopy(hive_tools.specs(names))
    for sp in out:
        fn = sp["function"]
        if fn["name"] == "rackup_invoke":
            fn["parameters"]["properties"]["payload"] = {"type": "object", "properties": copy.deepcopy(TEACHER_PAYLOAD_SCHEMA),
                                                         "additionalProperties": False}
            fn["description"] += " Payload keys per ability: " + "; ".join(
                f"{ab}: {', '.join(k)}" for ab, k in RACKUP_PAYLOADS.items()) + " (no other keys)."
    return out


# trade mode (opt-in targets; plan must name them): offered with the trade tools, executed offline on the sim backend
TRADE_TARGETS = ("trade_propose", "trade_research")
# what a correct routing looks like per target (a row that routes elsewhere is rejected)
ACCEPT_TOOLS = {"list_agents": {"list_agents", "route_to_agent"}, "route_to_agent": {"route_to_agent", "list_agents"},
                # "can RealAI do X?" may legitimately be answered by an ability OR an agent; both are hive routing
                "ability_lookup": {"ability_lookup", "list_agents", "route_to_agent"},
                "plugin_lookup": {"plugin_lookup", "plugin_registry_list"},
                "plugin_registry_list": {"plugin_registry_list", "plugin_lookup"},
                "module_lookup": {"module_lookup", "organs_hive_status"},
                "memory_stats": {"memory_stats", "memory_search"},
                "agent_pipeline_plan": {"agent_pipeline_plan", "hive_routes_status"},
                "hive_routes_status": {"hive_routes_status", "agent_pipeline_plan"},
                "tool_registry_lookup": {"tool_registry_lookup", "ability_lookup"},
                "repo_search": {"repo_search"},
                "trade_propose": {"trade_propose", "request_approval"}, "trade_research": {"trade_research"}}
_DISC = ("8-ball", "9-ball", "10-ball", "one pocket", "pyramid")


def home() -> Path:
    return Path(os.environ.get("REALAI_HOME") or Path.cwd()).resolve()


def out_dir() -> Path:
    d = home() / "datasets" / "_sources" / "hive_selfplay"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fens(n: int, rng: random.Random) -> List[str]:
    import chess

    p = home() / "datasets" / "_sources" / "lichess_puzzles_sample.csv"
    if not p.is_file():
        return []
    rows = list(csv.DictReader(p.open(encoding="utf-8")))
    out = []
    for r in rng.sample(rows, min(n, len(rows))):
        b = chess.Board(r["FEN"])
        b.push_uci(r["Moves"].split()[0])
        out.append(b.fen())
    return out


def seeds(tool: str, rng: random.Random, n: int) -> str:
    if tool == "chess_engine":
        f = _fens(n, rng)
        return "Use exactly these FEN positions, one per request, copied verbatim:\n" + "\n".join(f) if f else ""
    if tool == "shot_lookup":
        names = [s["name"] for s in hive_tools.shots()]
        return "Shots in the catalogue: " + ", ".join(rng.sample(names, min(12, len(names)))) if names else ""
    if tool == "rackup_invoke":
        kinds = ["how many points / what race wins RackUp Pyramid on a 7ft or 9ft table at a given skill level "
                 "(beginner, intermediate, advanced, pro)",
                 "converting an APA skill level (2-7) or a Fargo rating (300-750) to the RackUp/ROC scale",
                 "validating a league match submission: give scores (e.g. 5-3), the opponent id (p2, p17...) and the discipline, "
                 "or say no scores were entered yet"]
        return ("RackUp read-only abilities: pyramid_rules (payload table_size 7ft|9ft, skill_level beginner|intermediate|advanced|pro, "
                "optional my_score/opp_score), rating_convert (payload from_system apa|fargo|tap|bca, from_value), "
                "league_validate (payload my_score, opp_score, opponent_id, discipline). Spread the requests over: "
                + "; ".join(rng.sample(kinds, len(kinds))) + ". Never ask about a NEW rating after a match.")
    if tool == "ability_lookup":
        ab = rng.sample(hive_tools.abilities(), min(10, len(hive_tools.abilities())))
        return ("Each request must name ONE of these RealAI abilities (by its name) and ask whether it is live, "
                "what its status is, or how to call it. Do not ask about products or abilities not in this list.\n"
                "Abilities: " + "; ".join(f"{a['name']} (id {a['id']})" for a in ab))
    if tool == "data_analysis":
        return ("Each request must include the actual data inline: 5-12 short numbers (a plain comma list, or "
                "label: value pairs), and ask for specific statistics (mean, median, standard deviation, quartiles, "
                "min/max/range, outliers or trend). Never refer to data that is not in the request "
                "(no 'our database', 'last year', attached files).")
    if tool in ("list_agents", "route_to_agent"):
        pool = hive_tools.agents()
        must = [a for a in pool if a["id"] in ("security-engineer", "cybersecurity-expert", "accessibility-auditor")]
        ag = must[: rng.randint(1, len(must))] if must and tool == "route_to_agent" and rng.random() < 0.5 else []
        ag += rng.sample([a for a in pool if a not in ag], min(8 - len(ag), len(pool) - len(ag)))
        lead = ("Each request is a concrete job for ONE of these agents (draft, review, plan, design, analyse...), in the "
                "user's words; do not name the agent id. " if tool == "route_to_agent" else "")
        return lead + "Hive agents: " + "; ".join(f"{a['id']}: {str(a.get('description', ''))[:110]}" for a in ag)
    if tool == "device_profile":
        return "Questions are about THIS machine (no hardware details needed), e.g. which model/quant/GPU to run locally."
    if tool in ("rating_update_preview", "matchmaking_suggest", "rating_intel"):
        return ("Every request must include the numbers inline: ROC ratings are 200-800 (e.g. 520), optional RD 40-175. "
                + {"rating_update_preview": "Give my rating, my opponent's rating and whether I won or lost.",
                   "matchmaking_suggest": "Give my rating and 2-5 named opponents with their ratings.",
                   "rating_intel": "Give my current rating and 3-8 past ratings in order."}[tool])
    if tool in ("game_rules", "coach_drill"):
        return "Disciplines: " + ", ".join(_DISC) + (". Include a rating 300-750 and optionally minutes." if tool == "coach_drill" else ".")
    if tool == "hall_context":
        return "Each request names a table size (7ft or 9ft) and optionally a skill level (beginner/intermediate/advanced/pro)."
    if tool == "module_lookup":
        ms = [m["id"] for m in _safe(lambda: __import__("realai.hive_tools.extended", fromlist=["x"]).modules_index())]
        return "RealAI modules: " + ", ".join(rng.sample(ms, min(12, len(ms)))) if ms else ""
    if tool in ("plugin_lookup", "plugin_registry_list"):
        ps = [p["id"] for p in _safe(lambda: __import__("realai.hive_tools.extended", fromlist=["x"]).plugins_index())]
        return "RealAI plugins: " + ", ".join(ps) if ps else ""
    if tool == "organs_hive_status":
        return "Ask about the synthetic organs hive: how many organs, is it complete, how many in a category " \
               "(cognitive, nervous, dream, body, metabolic, evolution, memory_ecosystem, meta)."
    if tool == "memory_search":
        return "Ask RealAI to search its hive memory for a topic (chess, RackUp, training, a project name)."
    if tool == "approval_status":
        return "Ask what human approvals are pending/approved/rejected. Never ask to approve anything."
    if tool == "memory_stats":
        return "Ask how much is in RealAI's hive memory overall or in one namespace (default, chess, rackup, training)."
    if tool == "agent_pipeline_plan":
        return "Give a concrete task (code, design, summary, memory recall) and ask how the multi-agent pipeline would " \
               "split it up / which model each stage uses. Never ask it to actually run anything."
    if tool == "hive_routes_status":
        return "Ask about the hive router: which routes exist, which model a role uses (coder, architect, overseer, " \
               "analyst, memory, governor, router), whether hive mode is available, which hive agents are present."
    if tool == "payout_check":
        return "Each request lists final standings (2-4 names in order) and payout amounts in dollars per player, and asks " \
               "whether the payouts line up. Never ask to send or release money."
    if tool == "tool_registry_lookup":
        return "Ask whether RealAI has a tool for something (ledger audit, rating update, image, translation, chess, " \
               "memory) and what its source/status/parameters are."
    if tool == "self_heal_status":
        return "Ask for the self-heal status report: is it enabled, which artifacts are missing, promote queue size. " \
               "Never ask it to heal or promote."
    if tool == "executive_goals":
        return "Ask about the executive loop's goals: how many, which are open, which watchers run. Never ask it to act."
    if tool == "repo_search":
        from realai.hive_tools import repo_search as R

        have = R.available(R.mirror_root())
        return ("Each request is about ONE of Travis's own repos, named in the request: where a function/class is defined, "
                "what a repo's README says, what is in a folder, or which repo has some code. Repos: "
                + (", ".join(have) if have else "Rack_em_up, overseer-bot-ai, agent-tools, RealAi")
                + ". Never ask to run, deploy, trade, edit or show secret files (.env, keys).")
    if tool == "trade_propose":
        return ("Each request asks RealAI to buy or swap a SMALL amount on Solana with the bot wallet: $1-$5 of JUP (or its mint "
                "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN), paid in USDC or SOL, sometimes with a slippage limit (50-300 bps). "
                "Occasionally ask for more than $5 or more slippage than 300 bps. Never ask to send or transfer funds, change caps, "
                "touch the kill switch or reveal keys. Write only what the user says: never the outcome or the word PENDING.")
    if tool == "trade_research":
        return ("Each request is READ-ONLY trading research: a spot price (SOL, JUP, BTC, ETH, BONK), whether a Solana token mint is "
                "safe (JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN or a random mint), the paper account status, the kill switch / caps "
                "status, feed health, or a backtest (dca, grid, momentum, meanReversion, dipBuy on SOL or JUP). Never ask to trade.")
    if tool == "request_approval":
        return ("Each request asks RealAI to change or run ONE concrete thing, with every detail inline: replace an exact "
                "phrase in README.md with new text (quote both), create docs/notes-<topic>.md with given content, run a "
                "command such as 'git status' or 'pytest -q tests/test_merge_versions.py', run a short Python snippet "
                "(include the code), run self_repair, or promote self-heal gold. Occasionally ask to send SOL or release "
                "payouts. Write only what the user says: never the expected outcome, status or the word PENDING.")
    return ""


def _safe(fn):
    try:
        return fn() or []
    except Exception:
        return []


_THINK = re.compile(r"<think>.*?(</think>|$)", re.S)
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)
_Q_KEYS = ("question", "request", "query", "prompt", "text", "user", "content", "q", "message")


def extract_questions(text: str) -> List[str]:
    """Tolerant: strips <think>, code fences; accepts arrays of strings or objects; falls back to list lines."""
    t = _THINK.sub("", str(text or "")).strip()
    cands = [m.group(1) for m in _FENCE.finditer(t)] + [t]
    for c in cands:
        out: List[str] = []
        end = -1
        for m in re.finditer(r"\[", c):  # every '[' as a possible array start; raw_decode stops at its end
            if m.start() < end:
                continue  # inside an array already decoded
            try:
                arr, n = json.JSONDecoder().raw_decode(c[m.start():])
            except json.JSONDecodeError:
                continue
            got = []
            for x in arr if isinstance(arr, list) else []:
                if isinstance(x, dict):
                    x = next((x[k] for k in _Q_KEYS if isinstance(x.get(k), str)), None) or next(
                        (v for v in x.values() if isinstance(v, str) and len(v) > 8), None)
                if isinstance(x, str) and 8 < len(x.strip()) < 600:
                    got.append(x.strip())
            if got:
                out += got  # teachers sometimes emit one single-element array per request
                end = m.start() + n
        if out:
            return out
    lines = [re.sub(r"^\s*(?:[-*\u2022]|\d+[.)])\s*", "", ln).strip().strip('"') for ln in t.splitlines()]
    return [ln for ln in lines if 15 < len(ln) < 600 and (ln.endswith("?") or ln.endswith(".")) and not ln.startswith(("{", "["))]


def fallback_questions(tool: str, n: int, rng: random.Random) -> List[str]:
    """Template questions (grounded seeds) when the teacher returns nothing usable."""
    if tool == "chess_engine":
        return [f"What's the best move here? {f}" for f in _fens(n, rng)]
    if tool == "rackup_invoke":
        out = [f"How many points to win RackUp Pyramid on a {t} table at {s} level?" for t in ("7ft", "9ft")
               for s in ("beginner", "intermediate", "advanced", "pro")]
        out += [f"Convert {sy} {v} to the RackUp/ROC scale." for sy, v in (("APA", 3), ("APA", 6), ("Fargo", 480), ("Fargo", 650))]
        out += ["Validate my league match: I won 5-3 against opponent p2 in eight ball."]
    elif tool == "shot_lookup":
        out = [f"{p} the {s['name']} shot?" for s in hive_tools.shots() for p in ("What's the route for", "Any tip for")]
    elif tool == "math_solver":
        out = [f"Solve {a}x + {b} = {c} for x." for a, b, c in ((3, 4, 19), (5, -2, 23), (7, 3, 52))] + ["What is the derivative of x**3 + 2*x?"]
    elif tool == "data_analysis":
        out = []
        for _ in range(max(n, 4)):
            xs = [rng.randint(1, 99) for _ in range(rng.randint(5, 10))]
            ask = rng.choice(["mean, median and standard deviation", "quartiles and range", "min, max and any outliers",
                              "the trend", "mean and spread"])
            out.append(f"What are the {ask} of {', '.join(map(str, xs))}?")
    elif tool == "ability_lookup":
        tpl = ["Is the {n} ability live in RealAI?", "What's the status of {n}, and how do I call it?",
               "Can RealAI do {n} right now?", "How do I invoke RealAI's {n} ability?"]
        out = [rng.choice(tpl).format(n=a["name"]) for a in hive_tools.abilities()]
    elif tool in ("list_agents", "route_to_agent"):
        out = [f"Who in the hive should handle this: {str(a.get('description', ''))[:140]}" for a in hive_tools.agents() if a.get("description")]
    elif tool == "device_profile":
        out = ["What model and quant should you run on this PC?", "Which GPU should llama-server use on this machine?"]
    elif tool == "repo_search":
        from realai.hive_tools import repo_search as R

        have = R.available(R.mirror_root()) or ["Rack_em_up", "overseer-bot-ai", "agent-tools"]
        out = [t.format(r=r) for r in have for t in ("What's at the top level of my {r} repo?", "What does the README of {r} say it is?")]
    else:
        out = new_tool_templates(tool, n, rng)
    rng.shuffle(out)
    return out[:n]


def new_tool_templates(tool: str, n: int, rng: random.Random) -> List[str]:
    """Grounded template questions for the wire-audit tools (numbers inline, ids from the live indexes)."""
    r = lambda a, b: rng.randrange(a, b, 5)  # noqa: E731
    out: List[str] = []
    for _ in range(max(n, 4)):
        if tool == "rating_update_preview":
            me, op = r(380, 700), r(380, 700)
            out.append(rng.choice([f"I'm rated {me} and just {{w}} against a {op}. What's my new rating?",
                                   f"Preview my ROC rating: me {me}, opponent {op}, I {{w}}."]).format(w=rng.choice(["won", "lost"])))
        elif tool == "matchmaking_suggest":
            me = r(400, 680)
            opp = ", ".join(f"{nm} {r(350, 750)}" for nm in rng.sample(["Ana", "Ben", "Cruz", "Dee", "Eli", "Fox"], rng.randint(2, 4)))
            out.append(f"My rating is {me}. Who's the best match from: {opp}?")
        elif tool == "rating_intel":
            hist = sorted(r(380, 700) for _ in range(rng.randint(3, 6)))
            hist = hist if rng.random() < 0.5 else hist[::-1]
            out.append(f"My ratings went {', '.join(map(str, hist))}. Am I trending up or down?")
        elif tool == "game_rules":
            out.append(rng.choice(["What are the key rules of {d}?", "How do you rack and win in {d}?", "What fouls apply in {d}?"])
                       .format(d=rng.choice(_DISC)))
        elif tool == "coach_drill":
            out.append(f"I'm a {r(300, 750)} rated player. Give me a {rng.choice([20, 30, 45, 60])}-minute {rng.choice(_DISC)} practice plan.")
        elif tool == "hall_context":
            out.append(f"On a {rng.choice(['7ft', '9ft'])} table at {rng.choice(['beginner', 'intermediate', 'advanced', 'pro'])} "
                       "level, how many points win RackUp Pyramid and is it call-shot?")
        elif tool == "module_lookup":
            ms = _safe(lambda: __import__("realai.hive_tools.extended", fromlist=["x"]).modules_index())
            if ms:
                m = rng.choice(ms)
                out.append(rng.choice(["What does RealAI's {i} module do?", "Is the {i} module present, and how is it imported?"]).format(i=m["id"]))
        elif tool == "plugin_lookup":
            ps = _safe(lambda: __import__("realai.hive_tools.extended", fromlist=["x"]).plugins_index())
            if ps:
                out.append(f"What is the {rng.choice(ps)['id']} plugin for?")
        elif tool == "plugin_registry_list":
            out.append(rng.choice(["Which plugins are in RealAI's plugin registry?", "List your registered plugins and versions."]))
        elif tool == "organs_hive_status":
            out.append(rng.choice(["How many synthetic organs does the hive have, and is it complete?",
                                   f"How many {rng.choice(['cognitive', 'memory_ecosystem', 'body', 'meta'])} organs are in the hive?"]))
        elif tool == "memory_search":
            out.append(f"Search your hive memory for anything about {rng.choice(['chess', 'RackUp', 'training', 'Atomic Fizz', '9dttt'])}.")
        elif tool == "approval_status":
            out.append(rng.choice(["Are there any pending approvals?", "How many approval requests are waiting on me?"]))
        elif tool == "memory_stats":
            out.append(rng.choice(["How many entries are in your hive memory?", "What namespaces does your memory have?",
                                   f"How many memories are stored in the {rng.choice(['default', 'chess', 'rackup', 'training'])} namespace?"]))
        elif tool == "agent_pipeline_plan":
            t = rng.choice(["refactor the rating module", "design a multi-module league scheduler", "summarize last week's matches",
                            "debug the shot-of-the-day checker", "recall what we stored about 9dttt", "plan a chess opening course"])
            out.append(rng.choice([f"How would your agent pipeline handle: {t}?", f"Dry-run the multi-agent plan to {t}. Which model runs each stage?"]))
        elif tool == "hive_routes_status":
            out.append(rng.choice(["Is hive mode available, and which hive agents are present?", "What routes does the hive router know?",
                                   f"Which model does the {rng.choice(['coder', 'architect', 'overseer', 'analyst', 'memory', 'governor', 'router'])} role use?"]))
        elif tool == "payout_check":
            names = rng.sample(["Ana", "Ben", "Cruz", "Dee", "Eli", "Fox"], rng.randint(2, 4))
            amts = sorted((r(20, 300) for _ in names), reverse=True)
            order = names if rng.random() < 0.6 else rng.sample(names, len(names))
            pays = ", ".join(f"{n} ${a}" for n, a in zip(order, amts))
            out.append(f"Final standings: {', '.join(names)}. Payouts: {pays}. Do the payouts line up with the standings?")
        elif tool == "tool_registry_lookup":
            out.append(f"Do you have a tool for {rng.choice(['ledger audit', 'rating update', 'image generation', 'translation', 'chess', 'memory search', 'code execution'])}? What's its status?")
        elif tool == "self_heal_status":
            out.append(rng.choice(["What's your self-heal status? Which artifacts are missing?", "Is self-heal enabled, and how many artifacts are present?"]))
        elif tool == "executive_goals":
            out.append(rng.choice(["What goals is your executive loop tracking?", "How many open executive goals are there, and which watchers run?"]))
        elif tool == "trade_propose":
            usd = rng.choice([1, 2, 3, 4, 5, 5, 12, 40])
            out.append(rng.choice([f"Buy ${usd} of JUP from the bot wallet.", f"Swap {usd} USDC into JUP, slippage {rng.choice([50, 100, 300])} bps.",
                                   f"Queue a ${usd} JUP buy on Solana for my approval."]))
        elif tool == "trade_research":
            out.append(rng.choice(["What's SOL at?", f"Is {rng.choice(['JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN', '9zXf3hQpLm2WvT8rKcYb6nE4sJd1uGaHkPq5RtVwXyZo'])} safe to buy?",
                                   "How's my paper account?", "Is the trading kill switch on?", f"Backtest {rng.choice(['dca', 'grid'])} on SOL."]))
        elif tool == "request_approval":
            out.append(rng.choice(["Run `git status` in the repo for me.", "Run pytest -q tests/test_merge_versions.py.",
                                   "In README.md, change the first line's title to 'RealAI hive'.", "Run self_repair on the stack.",
                                   "Promote the curated self-heal gold into the live tree.", "Send 2 SOL to my other wallet."]))
    return list(dict.fromkeys(out))


def load_seed_topics(paths: List[str], exclude: Optional[set] = None) -> List[str]:
    """Topics for the teacher's questions (30B seed hook): .txt/.md lines or markdown headings, .json (list of strings,
    or objects/dicts with title/name/topic/heading/question keys, nested), .jsonl (same keys per row). Deduplicated;
    anything that equals a spot-check question (``exclude``, normalised) is dropped so eval prompts never leak in."""
    from realai.training.dataset_builder.dedupe import normalize

    keys = ("topic", "title", "name", "heading", "question", "instruction", "prompt", "summary")
    out: List[str] = []

    def walk(x):
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, list):
            for y in x:
                walk(y)
        elif isinstance(x, dict):
            hit = [x[k] for k in keys if isinstance(x.get(k), str)]
            if hit:
                out.append(hit[0])
            for v in x.values():
                if isinstance(v, (list, dict)):
                    walk(v)

    for raw in paths:
        p = Path(raw)
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if p.suffix.lower() == ".json":
            try:
                walk(json.loads(text))
            except ValueError:
                pass
        elif p.suffix.lower() == ".jsonl":
            for line in text.splitlines():
                try:
                    walk(json.loads(line))
                except ValueError:
                    continue
        else:
            heads = [ln.lstrip("#").strip() for ln in text.splitlines() if ln.startswith("#")]
            out += heads or [ln.strip("-* ").strip() for ln in text.splitlines() if ln.strip()]
    ex = exclude or set()
    seen, topics = set(), []
    for t in out:
        t = re.sub(r"\s+", " ", str(t)).strip()[:160]
        k = normalize(t)
        if len(t) < 4 or k in seen or k in ex:
            continue
        seen.add(k)
        topics.append(t)
    return topics


def topic_focus(topics: List[str], rng: random.Random, k: int = 6) -> str:
    if not topics:
        return ""
    pick = rng.sample(topics, min(k, len(topics)))
    return "where they fit this tool, draw on these RealAI ecosystem topics: " + "; ".join(pick)


def propose(chat, tool: str, n: int, rng: random.Random, focus: str = "", why: Optional[Counter] = None) -> List[str]:
    spec = (hive_tools.SPECS.get(tool) or hive_tools.specs([tool])[0])["function"]
    prompt = (f"/no_think\nWrite {n} diverse, realistic user requests that RealAI should answer by calling the `{tool}` tool "
              f"({spec['description']}). Vary tone and length; write only the requests, no answers.{(' Focus: ' + focus) if focus else ''}\n"
              f"{seeds(tool, rng, n)}\nReturn ONLY a JSON array of strings, e.g. [\"...\", \"...\"].")
    why = why if why is not None else Counter()
    try:
        msg = chat([{"role": "user", "content": prompt}], None)
        text = str(msg.get("content") or "") or str(msg.get("reasoning_content") or "")
        qs = extract_questions(text)[:n]
        if not text.strip():
            why["teacher_empty"] += 1
        elif not qs:
            why["teacher_unparseable"] += 1
    except Exception as exc:
        qs = []
        why[f"teacher_error:{type(exc).__name__}"] += 1
    if not qs:
        qs = fallback_questions(tool, n, rng)
        why["fallback_templates"] += 1 if qs else 0
        if not qs:
            why["no_fallback"] += 1
    return qs


def make_row(tool: str, res: Dict[str, Any], model: str) -> Dict[str, Any]:
    from realai.training.dataset_builder.adapters_tools import tool_subset

    called = [c["name"] for c in res["calls"]]
    msgs = res["messages"]
    return {"messages": msgs, "tools": hive_tools.specs(tool_subset(called, json.dumps(msgs[1:2]))),
            "verified": True, "tool": tool, "origin": "selfplay", "teacher": model,
            "ts": _dt.datetime.now().isoformat(timespec="seconds")}


def run(chat, model: str = "local", plan: Optional[Dict[str, int]] = None, minutes: float = 30, max_rows: int = 800,
        per_batch: int = 6, sleep: float = 0.0, seed: int = 0, judge: Optional[Callable[..., bool]] = None, propose_chat=None,
        log: Callable[[str], None] = print, seed_topics: Optional[List[str]] = None) -> Dict[str, Any]:
    from realai.training.dataset_builder.adapters_tools import TOOL_SYSTEM
    from realai.training.dataset_builder.dedupe import normalize
    from realai.training.dataset_builder.pipeline import eval_prompts

    eval_qs = eval_prompts()  # spot-check questions are never generated as training rows

    plan = plan or {t: 1 for t in TARGETS}
    weights = [(t, w) for t, w in plan.items() if (t in TARGETS or t in TRADE_TARGETS) and w > 0]
    t_specs = teacher_specs()
    t_trade_specs = teacher_specs(list(hive_tools.SPECS) + list(hive_tools.TRADE_TOOLS))
    rng = random.Random(seed or int(time.time()))
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    ok_p, rej_p = out_dir() / f"selfplay-{stamp}.jsonl", out_dir() / f"rejects-{stamp}.jsonl"
    deadline = time.time() + minutes * 60
    stats: Dict[str, Counter] = {}
    reasons: Counter = Counter()
    accepted = 0
    eng = None
    ctx: Dict[str, Any] = {}
    try:
        try:
            import chess.engine

            from abilities.chess_engine import find_engine

            path = find_engine()
            if path:
                eng = chess.engine.SimpleEngine.popen_uci(path)
                ctx["chess_engine_handle"] = eng
        except Exception:
            eng = None
        while time.time() < deadline and accepted < max_rows:
            tool = rng.choices([t for t, _ in weights], [w for _, w in weights])[0]
            st = stats.setdefault(tool, Counter())
            why: Counter = Counter()
            qs = propose(propose_chat or chat, tool, per_batch, rng, focus=topic_focus(seed_topics or [], rng), why=why)
            n_q = len(qs)
            qs = [q for q in qs if normalize(q) not in eval_qs]
            if len(qs) < n_q:
                st["eval_prompt_skipped"] += n_q - len(qs)
            st.update({"propose_" + k: v for k, v in why.items() if v})
            st["proposed"] += len(qs)
            if not qs:
                log(f"propose {tool}: 0 questions ({dict(why)})")
                time.sleep(2)
                continue
            for q in qs:
                if time.time() >= deadline or accepted >= max_rows:
                    break
                try:
                    trade = tool in TRADE_TARGETS
                    res = tool_loop.run(chat, [{"role": "system", "content": TOOL_SYSTEM + TEACHER_HINTS}, {"role": "user", "content": q}],
                                        tools=t_trade_specs if trade else t_specs, offline=True,
                                        ctx=dict(ctx, trade_backend="sim") if trade else ctx, project="hive")
                    res["messages"][0] = {"role": "system", "content": TOOL_SYSTEM}  # rows never carry the teacher hints
                except Exception as exc:
                    st["exec_error"] += 1
                    reasons[f"exec_error:{type(exc).__name__}"] += 1
                    continue
                called = {c["name"] for c in res["calls"]}
                ok, why = verify(res["messages"], res["calls"], judge=judge)
                if any(isinstance(c.get("arguments"), dict) and "_raw" in c["arguments"] for c in res["calls"]):
                    ok, why = False, ["truncated_tool_args"]  # model ran out of tokens mid tool-call JSON
                if ok and not (called & ACCEPT_TOOLS.get(tool, {tool})):
                    ok, why = False, ["wrong_tool:" + ",".join(sorted(called)) if called else "no_tool_call"]
                if ok:
                    accepted += 1
                    st["accepted"] += 1
                    with ok_p.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(make_row(tool, res, model), ensure_ascii=False) + "\n")
                else:
                    st["rejected"] += 1
                    reasons.update(r.split(":")[0] for r in why)
                    with rej_p.open("a", encoding="utf-8") as f:
                        f.write(json.dumps({"tool": tool, "question": q, "reasons": why, "calls": res["calls"],
                                            "answer": res["answer"]}, ensure_ascii=False, default=str) + "\n")
                if sleep:
                    time.sleep(sleep)
            log(f"[{_dt.datetime.now():%H:%M:%S}] {tool}: {dict(st)} total accepted {accepted}")
    except KeyboardInterrupt:
        log("interrupted: writing summary")
    finally:
        if eng is not None:
            eng.quit()
    summary = {"stamp": stamp, "accepted": accepted, "per_tool": {k: dict(v) for k, v in stats.items()},
               "reject_reasons": dict(reasons), "accepted_file": str(ok_p), "rejects_file": str(rej_p), "teacher": model,
               "plan": plan, "seed_topics": len(seed_topics or [])}
    (out_dir() / f"summary-{stamp}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def verify_traffic(judge=None) -> Dict[str, Any]:
    """Captured real traffic -> same verifier -> hive_selfplay/traffic-<date>.jsonl (money rows never replayed or kept)."""
    from .capture import traffic_dir

    stats: Counter = Counter()
    by_project: Dict[str, Counter] = {}
    stamp = _dt.date.today().isoformat()
    out = out_dir() / f"traffic-{stamp}.jsonl"
    seen_p = out_dir() / ".traffic_seen"
    seen = set(seen_p.read_text(encoding="utf-8").split()) if seen_p.is_file() else set()
    new_seen = []
    for p in sorted(traffic_dir().glob("*.jsonl")) if traffic_dir().is_dir() else []:
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines()):
            key = f"{p.name}:{i}"
            if key in seen or not line.strip():
                continue
            new_seen.append(key)
            r = json.loads(line)
            pc = by_project.setdefault(r.get("project", "realai"), Counter())
            pc["read"] += 1
            if not r.get("replay", True):
                pc["money_skipped"] += 1
                continue
            ok, why = verify(r["messages"], r.get("calls") or [], judge=judge)
            if not ok:
                pc["rejected"] += 1
                stats.update(x.split(":")[0] for x in why)
                continue
            pc["accepted"] += 1
            called = [c["name"] for c in r.get("calls") or []]
            from realai.training.dataset_builder.adapters_tools import tool_subset

            row = {"messages": r["messages"], "tools": hive_tools.specs(tool_subset(called, key)), "verified": True,
                   "tool": called[0] if called else None, "origin": f"traffic:{r.get('project')}", "ts": r.get("ts")}
            with out.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    if new_seen:
        with seen_p.open("a", encoding="utf-8") as f:
            f.write("\n".join(new_seen) + "\n")
    return {"per_project": {k: dict(v) for k, v in by_project.items()}, "reject_reasons": dict(stats), "out": str(out)}
