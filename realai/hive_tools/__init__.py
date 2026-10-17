"""Hive tool registry: the tools a RealAI model routes to (Qwen2.5 native tool calling).

One registry serves three places so they cannot drift:
  * dataset building (rows = user -> <tool_call> -> REAL tool output -> grounded answer),
  * the self-data loop (realai.training.self_data) and the spot-check gate,
  * the runtime tool loop (realai.hive_tools.tool_loop, used by the v3 orchestrator when opted in).

Safety: every tool here is read-only. Network tools (web_search, solana_read) are refused when
``offline=True`` (dataset generation always runs offline). Nothing here sends transactions,
trades, or writes files; RackUp is limited to read-only abilities.
"""
from __future__ import annotations

import json
import os
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "realai")):  # rackup_coach imports "plugins.rackup_coach"
    if _p not in sys.path:
        sys.path.append(_p)

RACKUP_READONLY = ("pyramid_rules", "rating_convert", "league_validate", "ledger_audit", "payout_sanity", "money_anomaly")


def _fn(name: str, desc: str, props: Dict[str, Any], required: List[str]) -> Dict[str, Any]:
    return {"type": "function", "function": {"name": name, "description": desc,
                                             "parameters": {"type": "object", "properties": props, "required": required}}}


_S = {"type": "string"}
SPECS: Dict[str, Dict[str, Any]] = {
    "chess_engine": _fn("chess_engine", "Local Stockfish: best move (SAN+UCI), eval and main line for a FEN.",
                        {"fen": _S, "depth": {"type": "integer"}}, ["fen"]),
    "rackup_invoke": _fn("rackup_invoke", "RackUp coach ability (read-only): " + ", ".join(RACKUP_READONLY) + ".",
                         {"ability": {"type": "string", "enum": list(RACKUP_READONLY)}, "payload": {"type": "object"}}, ["ability"]),
    "shot_lookup": _fn("shot_lookup", "Look up a RackUp catalogue shot (Shot of the Day) by id or name: setup, route, pocket, tip.",
                       {"query": _S}, ["query"]),
    "device_profile": _fn("device_profile", "Detect hardware (or take a given profile) and recommend model, quant, context and --device.",
                          {"profile": {"type": "object"}}, []),
    "math_solver": _fn("math_solver", "Solve/verify math with sympy (equations, derivatives, integrals, arithmetic).",
                       {"problem": _S}, ["problem"]),
    "data_analysis": _fn("data_analysis", "Descriptive statistics for a list of numbers or rows.",
                         {"data": {"type": "array", "items": {}}}, ["data"]),
    "ability_lookup": _fn("ability_lookup", "RealAI's own ability catalog: id, status (LIVE/PARTIAL/STUB), how to call it.",
                          {"query": _S}, ["query"]),
    "list_agents": _fn("list_agents", "Find hive agents (.agentx) matching a need.", {"query": _S}, ["query"]),
    "route_to_agent": _fn("route_to_agent", "Hand a task to a named hive agent.", {"agent": _S, "task": _S}, ["agent", "task"]),
    "web_search": _fn("web_search", "Web search (network; disabled offline).", {"query": _S}, ["query"]),
    "solana_read": _fn("solana_read", "Read-only Solana RPC lookup (balance/account); never sends (network).",
                       {"address": _S, "method": _S}, ["address"]),
}
NETWORK_TOOLS = {"web_search", "solana_read"}

from realai.hive_tools import extended as _ext  # noqa: E402  (read-only RackUp / self-knowledge / snapshot tools)

from realai.hive_tools import wired as _wired  # noqa: E402  (2026-10-16 wire-in: memory, multi-agent, money audit, registry, dry-run)

from realai.hive_tools import approvals as _apr  # noqa: E402  (request-only write/exec surface; never executes)

SPECS.update(_ext.SPECS)
SPECS.update(_wired.SPECS)
SPECS.update(_apr.SPECS)
NEW_TOOLS = tuple(_ext.SPECS) + tuple(_wired.SPECS) + tuple(_apr.SPECS)  # wire audit 2026-10-12 / 2026-10-16; improve.py starts them as weak
CORE_TOOLS = tuple(n for n in SPECS if n not in NEW_TOOLS)


def hive_tools_enabled() -> bool:
    """Live gate: the opt-in live tool loop offers the wire-audit tools only with REALAI_HIVE_TOOLS=1."""
    return os.environ.get("REALAI_HIVE_TOOLS", "").strip().lower() in ("1", "true", "yes", "on")


def key_facts(name: str, result: Dict[str, Any], args: Dict[str, Any]) -> List[List[str]]:
    if name in _wired.SPECS:
        return _wired.key_facts(name, result, args)
    if name in _apr.SPECS:
        return _apr.key_facts(name, result, args)
    return _ext.key_facts(name, result, args)


def specs(names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    return [SPECS[n] for n in (names or list(SPECS))]


def live_specs() -> List[Dict[str, Any]]:
    """Tools for the live (opt-in) tool loop: core tools, plus NEW_TOOLS only when REALAI_HIVE_TOOLS=1."""
    return specs(list(SPECS) if hive_tools_enabled() else list(CORE_TOOLS))


# ----------------------------------------------------------------------------- data sources
@lru_cache(maxsize=1)
def abilities() -> List[Dict[str, Any]]:
    from realai.ability_catalog import RUNDOWN_ABILITIES

    return [dict(r) for r in RUNDOWN_ABILITIES]


def _agents_path() -> Optional[Path]:
    for p in (os.environ.get("REALAI_AGENTS_JSON"), _ROOT / "agents" / "agentx" / "agents.json"):
        if p and Path(p).is_file():
            return Path(p)
    return None


@lru_cache(maxsize=1)
def agents() -> List[Dict[str, Any]]:
    p = _agents_path()
    if not p:
        return []
    d = json.loads(p.read_text(encoding="utf-8"))
    return [a for a in (d.get("agents", d) if isinstance(d, dict) else d) if a.get("id")]


def _shot_catalog_paths() -> List[Path]:
    out = []
    if os.environ.get("REALAI_SHOT_CATALOG"):
        out.append(Path(os.environ["REALAI_SHOT_CATALOG"]))
    home = Path(os.environ.get("REALAI_HOME") or _ROOT)
    out.append(home / "datasets" / "_sources" / "shot_catalog.json")
    return out


_SHOTS: Optional[List[Dict[str, Any]]] = None


def set_shot_catalog(shots: List[Dict[str, Any]]) -> None:
    global _SHOTS
    _SHOTS = list(shots)


def shots() -> List[Dict[str, Any]]:
    global _SHOTS
    if _SHOTS is None:
        _SHOTS = []
        for p in _shot_catalog_paths():
            if p.is_file():
                if p.suffix == ".json":
                    _SHOTS = json.loads(p.read_text(encoding="utf-8"))
                else:
                    from realai.training.dataset_builder.adapters import load_shot_catalog

                    _SHOTS = load_shot_catalog(p)
                break
    return _SHOTS


def _words(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 2}


def _rank(query: str, items: List[Dict[str, Any]], fields: List[str], k: int) -> List[Dict[str, Any]]:
    q = _words(query)
    low = query.lower().strip()
    scored = []
    for it in items:
        if low and (low == str(it.get("id", "")).lower() or low == str(it.get("name", "")).lower()):
            scored.append((100.0, it))
            continue
        text = " ".join(str(it.get(f, "")) if not isinstance(it.get(f), list) else " ".join(map(str, it.get(f))) for f in fields)
        w = _words(text)
        s = len(q & w) / (len(q) or 1)
        if s > 0:
            scored.append((s, it))
    scored.sort(key=lambda t: -t[0])
    return [it for _, it in scored[:k]]


# ----------------------------------------------------------------------------- executors (compact outputs)
def _chess(args, ctx):
    from abilities.chess_engine import analyse

    a = analyse(str(args.get("fen", "")), depth=int(args.get("depth") or ctx.get("chess_depth", 12)), engine=ctx.get("stockfish"),
                eng=ctx.get("chess_engine_handle"))
    if not a.get("ok"):
        return a
    keep = ("best_move_san", "best_move_uci", "eval", "pv_san", "side_to_move", "depth", "engine")
    return {"ok": True, **{k: a[k] for k in keep if k in a}}


def _rackup(args, ctx):
    ab = str(args.get("ability", ""))
    if ab not in RACKUP_READONLY:
        return {"ok": False, "error": f"ability {ab!r} not allowed (read-only set: {', '.join(RACKUP_READONLY)})"}
    from realai.plugins.rackup_coach import invoke

    payload = dict(args.get("payload") or {})
    r = invoke({"ability": ab, "player": {"id": "tool"}, "payload": payload})
    res = r.get("result") or {}
    if ab == "pyramid_rules":
        res = {"config": {k: v for k, v in (res.get("config") or {}).items() if k != "rules_notes"},
               "summary": res.get("coaching_summary"), "race": res.get("race") if payload.get("my_score") is not None else None}
    elif ab == "rating_convert":
        res = {k: res.get(k) for k in ("rackup_rating_estimate", "display", "confidence")} | {
            "equivalents": {k: (v or {}).get("display") for k, v in (res.get("equivalents") or {}).items()}}
    elif ab == "league_validate":
        res = {k: res.get(k) for k in ("valid", "errors", "warnings", "discipline")}
    return {"ok": bool(r.get("ok", True)), "ability": ab, "result": {k: v for k, v in res.items() if v is not None}}


def _shot(args, ctx):
    hits = _rank(str(args.get("query", "")), shots(), ["id", "name", "tagline", "category"], 1)
    if not hits:
        return {"ok": False, "error": "no catalogue shot matches", "catalogue_size": len(shots())}
    s = hits[0]
    route = next((x for x in s.get("setup", []) if str(x).startswith("Route:")), None)
    return {"ok": True, "id": s.get("id"), "name": s.get("name"), "what": s.get("what"), "route": route,
            "setup": [x for x in s.get("setup", []) if not str(x).startswith("Route:")], "pocket": s.get("pocket"),
            "tip": s.get("tipDetail"), "difficulty": s.get("difficulty"), "category": s.get("category")}


def _device(args, ctx):
    from realai.core.device_profile import collect, recommend

    prof = args.get("profile") or collect()
    return {"ok": True, "recommendation": recommend(prof)}


def _math(args, ctx):
    from abilities.math_solver import solve

    r = solve(str(args.get("problem", "")))
    return {k: r.get(k) for k in ("ok", "kind", "answer", "verified", "method", "error") if r.get(k) is not None}


def _data(args, ctx):
    from abilities.data_analysis import run

    r = run(context={"data": args.get("data")})
    r.pop("ability", None)
    return r


def _ability(args, ctx):
    hits = _rank(str(args.get("query", "")), abilities(), ["id", "name", "keywords"], 3)
    return {"ok": bool(hits), "matches": [{"id": h["id"], "name": h["name"], "status": h["status"], "live_path": h.get("live_path")}
                                          for h in hits]}


def _list_agents(args, ctx):
    hits = _rank(str(args.get("query", "")), agents(), ["id", "role", "description", "tags"], 3)
    return {"ok": bool(hits), "agents": [{"id": a["id"], "role": a.get("role"), "about": str(a.get("description", ""))[:160]} for a in hits]}


def _route(args, ctx):
    """Hand-off through the REAL hive runtime (realai.orchestration.hive_router.run_cycle) in dry-run mode:
    routes and model are resolved exactly as a live cycle would; nothing runs, nothing is persisted."""
    aid = str(args.get("agent", "")).strip()
    a = next((x for x in agents() if x["id"] == aid or str(x.get("role", "")).lower() == aid.lower()), None)
    if not a:
        return {"ok": False, "error": f"no agent {aid!r}; call list_agents first"}
    from realai.orchestration.hive_router import run_cycle

    task = str(args.get("task", ""))[:300] or "status"
    plan = run_cycle(task, agent=a["id"], persist=False, dry_run=True)
    return {"ok": bool(plan.get("ok")), "handoff": {"agent": a["id"], "role": a.get("role"), "task": task,
                                                    "status": "planned (dry run)", "model": plan.get("model"),
                                                    "stages": (plan.get("plan") or {}).get("stages"),
                                                    "hive_mode": (plan.get("routes") or {}).get("hive_mode"),
                                                    "runs_via": "hive_router.run_cycle"}}


def _network(args, ctx):
    return {"ok": False, "error": "network tool disabled (offline)"}


def _web(args, ctx):
    from abilities.web_search import run

    return run(input=str(args.get("query", "")))


def _solana(args, ctx):
    from abilities.web3_integration import run

    return run(input=str(args.get("address", "")), context={"action": args.get("method") or "balance", "read_only": True})


EXECUTORS: Dict[str, Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]] = {
    "chess_engine": _chess, "rackup_invoke": _rackup, "shot_lookup": _shot, "device_profile": _device,
    "math_solver": _math, "data_analysis": _data, "ability_lookup": _ability, "list_agents": _list_agents,
    "route_to_agent": _route, "web_search": _web, "solana_read": _solana,
    **_ext.EXECUTORS,
    **_wired.EXECUTORS,
    **_apr.EXECUTORS,
}
SANDBOXED_TOOLS = set(_apr.SPECS)  # offline (self_data / spotcheck / verify) -> private temp approvals store


def execute(name: str, args: Any, offline: bool = True, ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run one tool. Never raises; returns {"ok": False, "error": ...} on failure."""
    if isinstance(args, str):
        try:
            args = json.loads(args or "{}")
        except json.JSONDecodeError:
            return {"ok": False, "error": "arguments are not JSON"}
    if name not in EXECUTORS:
        return {"ok": False, "error": f"unknown tool {name!r}"}
    if offline and name in NETWORK_TOOLS:
        return _network(args, ctx or {})
    if offline and name in SANDBOXED_TOOLS:
        ctx = {**(ctx or {}), "approvals_sandbox": True}
    try:
        return EXECUTORS[name](dict(args or {}), ctx or {})
    except Exception as exc:  # tools must not crash the loop
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:300]}


def tool_json(result: Dict[str, Any], limit: int = 1400) -> str:
    s = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    return s if len(s) <= limit else s[: limit - 1] + "…"
