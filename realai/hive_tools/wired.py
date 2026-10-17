"""Wire-in batch 2026-10-16: previously orphaned product code exposed as read-only / dry-run hive tools.

Batches (see docs/WIRING_STATUS.md):
  memory      memory_stats          hive memory store shape (namespaces, row counts) from a SNAPSHOT copy
  multi-agent agent_pipeline_plan   dry-run plan of agents.agent_runtime.MultiAgentPipeline (stages, roles,
                                    model per stage via realai.core_hive_router.route_model); no model calls
              hive_routes_status    realai.core_hive_router.register_routes(): routes, role models, hive agents
  money       payout_check          realai.plugins.rackup_coach.money_audit.payout_sanity (read-only; never
                                    authorizes or executes a payout)
  tools       tool_registry_lookup  realai.tools.ToolRegistry (builtins + ability catalog) merged with hive_tools
  dry-run     self_heal_status      realai.self_heal.status() report only (no heal, no promote, no writes)
              executive_goals       realai.executive goals.jsonl SNAPSHOT + watcher names (no tick, no act)

Same contract as ``extended``: deterministic for the same args/snapshot, no network, no sends, no money
actions, no writes outside a private temp snapshot dir. The verifier re-runs the executor and requires an
identical result plus the facts from ``key_facts``.

Live exposure is gated: the opt-in live tool loop only offers these when REALAI_HIVE_TOOLS=1
(see ``realai.hive_tools.live_specs``); self_data / spotcheck always see them.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from realai.hive_tools.extended import _fn, _home, _num, _rank, snapshot

_S = {"type": "string"}

SPECS: Dict[str, Dict[str, Any]] = {
    "memory_stats": _fn(
        "memory_stats", "Shape of RealAI hive memory (read-only snapshot): namespaces and how many entries each holds.",
        {"namespace": _S}, []),
    "agent_pipeline_plan": _fn(
        "agent_pipeline_plan", "Dry-run plan for the five-stage multi-agent pipeline (planner, researcher, critic, "
        "executor, synthesizer): what each stage does and which local model it routes to. Runs no model.",
        {"task": _S}, ["task"]),
    "hive_routes_status": _fn(
        "hive_routes_status", "Unified hive router status: route table, model per hive role, hive agents present, "
        "whether hive mode (all archetypes) is available.", {"role": _S}, []),
    "payout_check": _fn(
        "payout_check", "Read-only RackUp payout sanity check: do payout lines match final standings? "
        "Never authorizes or sends a payout.",
        {"standings": {"type": "array", "items": _S},
         "payouts": {"type": "array", "items": {"type": "object"}}}, ["standings", "payouts"]),
    "tool_registry_lookup": _fn(
        "tool_registry_lookup", "Look up RealAI's unified tool registry (builtins, ability catalog tools, hive tools): "
        "source, status, safety level, parameters.", {"query": _S}, ["query"]),
    "self_heal_status": _fn(
        "self_heal_status", "Self-heal report (dry run): enabled?, artifacts present/missing, promote queue size, "
        "ability coverage. Never heals, promotes or writes.", {}, []),
    "executive_goals": _fn(
        "executive_goals", "Executive loop goals (read-only snapshot): goal count, open goals, status counts, "
        "registered watchers. Never ticks or acts.", {"status": _S}, []),
}


# ----------------------------------------------------------------------------- memory
def memory_stats(args, ctx):
    src = Path(os.environ.get("REALAI_MEMORY_DB") or _home() / "memory" / "hive" / "memory.sqlite3")
    snap = snapshot("memory", src, ctx)
    out: Dict[str, Any] = {"ok": True, "snapshot": "memory.sqlite3 copy", "total": 0, "namespaces": {}}
    if not snap.is_file():
        out["snapshot"] = "empty (no memory.sqlite3)"
    else:
        con = sqlite3.connect(f"file:{snap}?mode=ro", uri=True)
        try:
            rows = con.execute("SELECT namespace, COUNT(*) FROM memory GROUP BY namespace ORDER BY namespace").fetchall()
        except sqlite3.Error:
            rows = []
        finally:
            con.close()
        out["namespaces"] = {str(n): int(c) for n, c in rows}
        out["total"] = sum(out["namespaces"].values())
    ns = str(args.get("namespace") or "").strip()
    if ns:
        out["namespace"] = ns
        out["namespace_count"] = out["namespaces"].get(ns, 0)
    return out


# ----------------------------------------------------------------------------- multi-agent
def _stage_role(prompt: str) -> str:
    first = prompt.split(". ")[0].strip().rstrip(".")
    return first.replace("You are ", "").replace("Your job is to ", "")


def agent_pipeline_plan(args, ctx):
    task = str(args.get("task") or "").strip()
    if not task:
        return {"ok": False, "error": "need task"}
    from agents.agent_runtime import MultiAgentPipeline
    from realai.core_hive_router import route_model

    stages = [{"stage": s, "role": _stage_role(MultiAgentPipeline.STAGE_SYSTEM_PROMPTS.get(s, "")),
               "model": route_model(s, task)} for s in MultiAgentPipeline.STAGES]
    return {"ok": True, "dry_run": True, "task": task[:200], "stage_count": len(stages), "stages": stages,
            "task_model": route_model("", task),
            "note": "plan only; no stage was executed and no model was called"}


def hive_routes_status(args, ctx):
    from realai.core_hive_router import HIVE_ARCHETYPES, register_routes

    r = register_routes()
    present = set(r.get("hive_agents") or [])
    out = {"ok": True, "route_count": len(r["routes"]), "routes": sorted(r["routes"]), "role_models": r["role_models"],
           "hive_agents": sorted(present), "hive_mode": bool(r["hive_mode"]),
           "missing_archetypes": [a for a in HIVE_ARCHETYPES if a not in present], "fallback": r["fallback"]}
    role = str(args.get("role") or "").strip().lower()
    if role:
        out["role"] = role
        out["role_model"] = r["role_models"].get(role)
    return out


# ----------------------------------------------------------------------------- money (read-only audit)
def payout_check(args, ctx):
    standings = [str(s).strip() for s in (args.get("standings") or []) if str(s).strip()]
    lines = []
    for i, p in enumerate(args.get("payouts") or []):
        if not isinstance(p, dict):
            continue
        amt = _num(p.get("amount", p.get("amount_dollars")))
        who = str(p.get("player") or p.get("player_id") or p.get("name") or "").strip()
        if amt is None or not who:
            continue
        place = int(_num(p.get("place", p.get("rank")), i + 1))
        lines.append({"player_id": who, "rank": place, "amount": int(round(amt * 100))})
    if not standings or not lines:
        return {"ok": False, "error": "need standings [names in finishing order] and payouts [{player, amount}]"}
    from realai.plugins.rackup_coach.money_audit import payout_sanity

    r = payout_sanity({"standings": [{"player_id": n, "rank": i + 1} for i, n in enumerate(standings)],
                       "payout_lines": lines})
    issues = [{"code": f.get("code"), "message": f.get("message")} for f in (r.get("blockers") or []) + (r.get("warnings") or [])]
    return {"ok": True, "status": r.get("status"), "release_safe": bool((r.get("gate") or {}).get("release_safe")),
            "ranks_match_standings": r.get("ranks_match_standings"),
            "total_payout_dollars": round((r.get("total_payout_lines_cents") or 0) / 100, 2),
            "issues": issues[:6], "summary": (r.get("plain_language") or [""])[0],
            "authorize_payout": False, "note": "audit only; RackUp releases payouts, RealAI never does"}


# ----------------------------------------------------------------------------- unified tool registry
def registry(include_hive: bool = True):
    """Fresh realai.tools.ToolRegistry (builtins + ability catalog) with hive_tools merged in."""
    import realai.tools as rt

    reg = rt.ToolRegistry()
    for s in rt.TOOL_REGISTRY.list_all():
        reg.register(s)
    if include_hive:
        register_into(reg)
    return reg


def register_into(reg) -> int:
    """Merge hive_tools SPECS into a realai.tools.ToolRegistry (source='hive_tools'). Returns count added."""
    from realai import hive_tools
    from realai.tools import ToolSchema

    n = 0
    for name, spec in hive_tools.SPECS.items():
        if reg.get(name) is not None:
            continue
        fn = spec["function"]
        params = fn.get("parameters") or {}
        reg.register(ToolSchema(name=name, description=fn.get("description", ""), parameters=params,
                                required=list(params.get("required") or []),
                                safety_level="network" if name in hive_tools.NETWORK_TOOLS else "safe",
                                source="hive_tools"))
        n += 1
    return n


def tool_registry_lookup(args, ctx):
    q = str(args.get("query") or "").strip()
    if not q:
        return {"ok": False, "error": "need query"}
    reg = registry()
    items = [{"id": s.name, "description": s.description, "source": s.source, "status": s.ability_status or "",
              "safety": s.safety_level, "params": sorted((s.parameters or {}).get("properties", {}))[:8]}
             for s in reg.list_all()]
    by_src: Dict[str, int] = {}
    for it in items:
        by_src[it["source"]] = by_src.get(it["source"], 0) + 1
    hits = _rank(q, items, ("id", "description"), k=3)
    return {"ok": True, "total": len(items), "by_source": dict(sorted(by_src.items())),
            "tools": [{k: v for k, v in h.items()} for h in hits]}


# ----------------------------------------------------------------------------- dry-run reports
def self_heal_status(args, ctx):
    from realai import self_heal

    s = self_heal.status()
    art = s.get("artifacts") or {}
    return {"ok": True, "dry_run": True, "enabled": bool(s.get("enabled")),
            "artifacts_present": sum(1 for v in art.values() if v), "artifacts_total": len(art),
            "missing": sorted(k for k, v in art.items() if not v)[:12],
            "promote_queue_items": s.get("promote_queue_items"), "promote_actionable": s.get("promote_actionable"),
            "note": "report only; self_data never runs heal/promote"}


def _goals_file() -> Path:
    # same location as realai.executive.goal.goals_path, without its mkdir side effect
    root = Path(os.environ.get("REALAI_WORKSPACE") or _home())
    return root / "realai" / "executive" / "state" / "goals.jsonl"


def executive_goals(args, ctx):
    from realai.executive.goal import Goal
    from realai.executive.watchers import WATCHER_NAMES

    snap = snapshot("exec_goals", _goals_file(), ctx)
    latest: Dict[str, Any] = {}
    if snap.is_file():
        for line in snap.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
                g = Goal.from_dict(row.get("goal") or row)
                latest[g.id] = g
            except Exception:
                continue
    goals = list(latest.values())
    counts: Dict[str, int] = {}
    for g in goals:
        counts[str(g.status)] = counts.get(str(g.status), 0) + 1
    want = str(args.get("status") or "open").lower()
    sel = [{"id": g.id, "status": g.status, "title": str(getattr(g, "title", "") or getattr(g, "text", ""))[:120]}
           for g in goals if str(g.status).lower() == want][:10]
    return {"ok": True, "total": len(goals), "by_status": dict(sorted(counts.items())), "status": want, "goals": sel,
            "watchers": list(WATCHER_NAMES), "note": "read-only snapshot; the executive daemon is not ticked"}


EXECUTORS = {"memory_stats": memory_stats, "agent_pipeline_plan": agent_pipeline_plan,
             "hive_routes_status": hive_routes_status, "payout_check": payout_check,
             "tool_registry_lookup": tool_registry_lookup, "self_heal_status": self_heal_status,
             "executive_goals": executive_goals}

BATCHES = {"memory": ["memory_stats"], "multi_agent": ["agent_pipeline_plan", "hive_routes_status"],
           "money_readonly": ["payout_check"], "tools_registry": ["tool_registry_lookup"],
           "dry_run_reports": ["self_heal_status", "executive_goals"]}


def key_facts(name: str, r: Dict[str, Any], args: Dict[str, Any]) -> List[List[str]]:
    def num(x):
        if x is None:
            return []
        f = float(x)
        return [f"{f:.0f}", f"{f:.1f}", f"{f:.2f}", str(x)]
    none = ["no ", "none", "0", "zero", "empty", "nothing"]
    if name == "memory_stats":
        if "namespace_count" in r:
            return [num(r["namespace_count"]) + (none if not r["namespace_count"] else [])]
        return [num(r.get("total")) + (none if not r.get("total") else [])]
    if name == "agent_pipeline_plan":
        return [[s["model"] for s in r.get("stages") or []], ["planner", "Planner"]]
    if name == "hive_routes_status":
        if r.get("role_model"):
            return [[str(r["role_model"])]]
        return [num(r.get("route_count")) + [str(len(r.get("hive_agents") or []))]]
    if name == "payout_check":
        if r.get("error") and "status" not in r:
            return []  # argument-validation error (model retries with fixed args); the retried call is what gets checked
        if r.get("release_safe"):
            return [[str(r.get("status")), "checks out", "check out", "consistent", "safe to release", "align",
                     "correctly", "is correct", "are correct", "line up", "lines up", "safe for rackup"]]
        return [[str(r.get("status")), "not safe", "mismatch", "block", "issue", "problem", "wrong", "don't match",
                 "doesn't match", "not match"]]
    if name == "tool_registry_lookup":
        return [[str(t.get("id")) for t in r.get("tools") or []] + [str(t.get("id")).replace("_", " ").replace("ability.", "")
                                                                    for t in r.get("tools") or []]]
    if name == "self_heal_status":
        return [num(r.get("artifacts_present")) + num(r.get("artifacts_total"))]
    if name == "executive_goals":
        return [[str(r.get("total"))] + (none + ["no " + str(r.get("status"))] if not r.get("goals") else [])]
    return []
