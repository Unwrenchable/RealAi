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
           "list_agents", "route_to_agent", "device_profile")
# what a correct routing looks like per target (a row that routes elsewhere is rejected)
ACCEPT_TOOLS = {"list_agents": {"list_agents", "route_to_agent"}, "route_to_agent": {"route_to_agent", "list_agents"}}


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
        return ("RackUp read-only abilities: pyramid_rules (payload table_size 7ft|9ft, skill_level beginner|intermediate|advanced|pro, "
                "optional my_score/opp_score), rating_convert (payload from_system apa|fargo|tap|bca, from_value), "
                "league_validate (payload my_score, opp_score, opponent_id, discipline).")
    if tool == "ability_lookup":
        ab = rng.sample(hive_tools.abilities(), min(10, len(hive_tools.abilities())))
        return "Some RealAI abilities: " + "; ".join(f"{a['name']} ({a['status']})" for a in ab)
    if tool in ("list_agents", "route_to_agent"):
        ag = rng.sample(hive_tools.agents(), min(8, len(hive_tools.agents())))
        return "Hive agents: " + "; ".join(f"{a['id']}: {str(a.get('description', ''))[:110]}" for a in ag)
    if tool == "device_profile":
        return "Questions are about THIS machine (no hardware details needed), e.g. which model/quant/GPU to run locally."
    return ""


def propose(chat, tool: str, n: int, rng: random.Random, focus: str = "") -> List[str]:
    spec = hive_tools.SPECS[tool]["function"]
    prompt = (f"Write {n} diverse, realistic user requests that RealAI should answer by calling the `{tool}` tool "
              f"({spec['description']}). Vary tone and length; no answers.{(' Focus: ' + focus) if focus else ''}\n"
              f"{seeds(tool, rng, n)}\nReturn ONLY a JSON array of strings.")
    msg = chat([{"role": "user", "content": prompt}], None)
    text = str(msg.get("content") or "")
    m = re.search(r"\[.*\]", text, re.S)
    try:
        qs = json.loads(m.group(0)) if m else []
    except json.JSONDecodeError:
        qs = []
    return [q.strip() for q in qs if isinstance(q, str) and 8 < len(q.strip()) < 600][:n]


def make_row(tool: str, res: Dict[str, Any], model: str) -> Dict[str, Any]:
    from realai.training.dataset_builder.adapters_tools import tool_subset

    called = [c["name"] for c in res["calls"]]
    msgs = res["messages"]
    return {"messages": msgs, "tools": hive_tools.specs(tool_subset(called, json.dumps(msgs[1:2]))),
            "verified": True, "tool": tool, "origin": "selfplay", "teacher": model,
            "ts": _dt.datetime.now().isoformat(timespec="seconds")}


def run(chat, model: str = "local", plan: Optional[Dict[str, int]] = None, minutes: float = 30, max_rows: int = 800,
        per_batch: int = 6, sleep: float = 0.0, seed: int = 0, judge: Optional[Callable[..., bool]] = None, propose_chat=None,
        log: Callable[[str], None] = print) -> Dict[str, Any]:
    from realai.training.dataset_builder.adapters_tools import TOOL_SYSTEM

    plan = plan or {t: 1 for t in TARGETS}
    weights = [(t, w) for t, w in plan.items() if t in TARGETS and w > 0]
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
            try:
                qs = propose(propose_chat or chat, tool, per_batch, rng)
            except Exception as exc:
                st["propose_error"] += 1
                log(f"propose {tool} failed: {exc}")
                time.sleep(2)
                continue
            st["proposed"] += len(qs)
            for q in qs:
                if time.time() >= deadline or accepted >= max_rows:
                    break
                try:
                    res = tool_loop.run(chat, [{"role": "system", "content": TOOL_SYSTEM}, {"role": "user", "content": q}],
                                        offline=True, ctx=ctx, project="hive")
                except Exception as exc:
                    st["exec_error"] += 1
                    reasons[f"exec_error:{type(exc).__name__}"] += 1
                    continue
                called = {c["name"] for c in res["calls"]}
                ok, why = verify(res["messages"], res["calls"], judge=judge)
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
    finally:
        if eng is not None:
            eng.quit()
    summary = {"stamp": stamp, "accepted": accepted, "per_tool": {k: dict(v) for k, v in stats.items()},
               "reject_reasons": dict(reasons), "accepted_file": str(ok_p), "rejects_file": str(rej_p), "teacher": model,
               "plan": plan}
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
