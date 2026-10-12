"""Extended read-only hive tools (wire-audit 2026-10-12): RackUp rating/coach stack, self-knowledge
(modules, plugins, organs), and local stores read from a SNAPSHOT copy.

Every tool here is read-only and deterministic for the same arguments (and the same snapshot):
no network, no sends, no money actions, no writes outside a private temp snapshot dir.
Each executor calls the gold implementation (rackup_coach abilities, abilities/*_surface, plugin_registry,
modules.organs, hive_memory adapter, approval_store loader); the verifier re-runs the same executor and
requires an identical result (see ``realai.training.self_data.verify``).

Skipped: ``knowledge_query`` - realai.memory.knowledge_graph is an in-process graph with no persisted store,
so a fresh process has nothing to query and answers could not be grounded.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[2]
_S = {"type": "string"}
_N = {"type": "number"}


def _fn(name, desc, props, required):
    return {"type": "function", "function": {"name": name, "description": desc,
                                             "parameters": {"type": "object", "properties": props, "required": required}}}


SPECS: Dict[str, Dict[str, Any]] = {
    "rating_update_preview": _fn(
        "rating_update_preview", "Preview a post-match ROC Glicko-2 rating change (read-only; RackUp persists, RealAI never writes).",
        {"player_rating": _N, "player_rd": _N, "opponent_rating": _N, "opponent_rd": _N, "won": {"type": "boolean"},
         "discipline": _S}, ["player_rating", "opponent_rating", "won"]),
    "matchmaking_suggest": _fn(
        "matchmaking_suggest", "Rank candidate opponents for a player by ROC Glicko-2 fit (expected score, window).",
        {"player_rating": _N, "player_rd": _N, "discipline": _S,
         "candidates": {"type": "array", "items": {"type": "object"}}}, ["player_rating", "candidates"]),
    "rating_intel": _fn(
        "rating_intel", "Rating trajectory/intel from a player's rating history (climbing/stable/falling, band, volatility).",
        {"player_rating": _N, "rd": _N, "rating_history": {"type": "array", "items": _N}}, ["player_rating", "rating_history"]),
    "game_rules": _fn(
        "game_rules", "Rules for a pool discipline: 8-ball, 9-ball, 10-ball, one pocket, RackUp Pyramid.",
        {"discipline": _S}, ["discipline"]),
    "coach_drill": _fn(
        "coach_drill", "Rating-aware practice plan (drill blocks with minutes) for a discipline.",
        {"rating": _N, "discipline": _S, "minutes": {"type": "integer"}}, ["rating", "discipline"]),
    "hall_context": _fn(
        "hall_context", "Pool hall/session context: table size -> Pyramid rack, points to win, call-shot, scoring.",
        {"hall_name": _S, "table_size": _S, "skill_level": _S}, ["table_size"]),
    "module_lookup": _fn(
        "module_lookup", "RealAI's own modules (modules/ and realai/core): id, role, import path, present.",
        {"query": _S}, ["query"]),
    "plugin_lookup": _fn(
        "plugin_lookup", "RealAI's own plugins (realai/plugins + plugin registry): id, role, capabilities, version.",
        {"query": _S}, ["query"]),
    "plugin_registry_list": _fn(
        "plugin_registry_list", "List plugins in the RealAI plugin registry with version and capabilities.", {}, []),
    "organs_hive_status": _fn(
        "organs_hive_status", "Synthetic organs hive status: organ count, completeness, organs per category.",
        {"category": _S}, []),
    "memory_search": _fn(
        "memory_search", "Search RealAI hive memory (read-only snapshot of memory/hive/memory.sqlite3).",
        {"query": _S, "namespace": _S, "k": {"type": "integer"}}, ["query"]),
    "approval_status": _fn(
        "approval_status", "Read-only view of human approval requests (counts by status, pending items). Never approves.",
        {"status": _S}, []),
}
SKIPPED = {"knowledge_query": "realai.memory.knowledge_graph has no persisted store (in-process graph only); "
                              "nothing groundable to query from a fresh process"}


def _invoke(ability: str, player: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    from realai.plugins.rackup_coach import invoke

    return invoke({"ability": ability, "player": player, "payload": payload})


def _num(x, default=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


# ----------------------------------------------------------------------------- RackUp
def rating_update_preview(args, ctx):
    pr, orr = _num(args.get("player_rating")), _num(args.get("opponent_rating"))
    if pr is None or orr is None or "won" not in args:
        return {"ok": False, "error": "need player_rating, opponent_rating and won"}
    player = {"id": "player", "rating": pr, "rd": _num(args.get("player_rd"), 175.0)}
    payload = {"won": bool(args.get("won")), "opponent_rating": orr, "opponent_rd": _num(args.get("opponent_rd"), 175.0)}
    if args.get("discipline"):
        payload["discipline"] = str(args["discipline"])
    r = _invoke("rating_update", player, payload)
    res = r.get("result") or {}
    if not r.get("ok", True) or "rating_after" not in res:
        return {"ok": False, "error": r.get("error") or "rating_update failed"}
    keep = ("discipline", "rating_before", "rating_after", "delta", "rd_before", "rd_after", "display_before",
            "display_after", "band_changed")
    return {"ok": True, "won": payload["won"], "opponent_rating": orr, **{k: res.get(k) for k in keep}}


def matchmaking_suggest(args, ctx):
    pr = _num(args.get("player_rating"))
    cands = [c for c in (args.get("candidates") or []) if isinstance(c, dict) and _num(c.get("rating")) is not None]
    if pr is None or not cands:
        return {"ok": False, "error": "need player_rating and candidates [{id, rating, rd?}]"}
    cands = [{"id": str(c.get("id") or c.get("name") or f"c{i + 1}"), "rating": _num(c.get("rating")),
              "rd": _num(c.get("rd"), 175.0)} for i, c in enumerate(cands[:12])]
    payload = {"candidates": cands}
    if args.get("discipline"):
        payload["discipline"] = str(args["discipline"])
    r = _invoke("matchmaking", {"id": "player", "rating": pr, "rd": _num(args.get("player_rd"), 175.0)}, payload)
    res = r.get("result") or {}
    if not r.get("ok", True) or "ranked_candidates" not in res:
        return {"ok": False, "error": r.get("error") or "matchmaking failed"}
    rank = [{"id": c.get("id"), "rating": c.get("rating"), "expected_score": c.get("expected_score_vs_player"),
             "in_window": c.get("in_window")} for c in res["ranked_candidates"][:5]]
    return {"ok": True, "player_rating": pr, "best": rank[0]["id"] if rank else None, "ranked": rank,
            "window": res.get("recommended_window")}


def rating_intel(args, ctx):
    pr = _num(args.get("player_rating"))
    hist = [h for h in (_num(x) for x in (args.get("rating_history") or [])) if h is not None]
    if pr is None or not hist:
        return {"ok": False, "error": "need player_rating and rating_history (numbers)"}
    r = _invoke("rating_intel", {"id": "player", "rating": pr, "rd": _num(args.get("rd"), 175.0)},
                {"rating_history": [{"rating": h} for h in hist]})
    res = r.get("result") or {}
    if not r.get("ok", True) or not res:
        return {"ok": False, "error": r.get("error") or "rating_intel failed"}
    keep = ("current_rating", "display", "band_label", "trajectory", "delta_window", "history_volatility")
    return {"ok": True, **{k: res.get(k) for k in keep}}


def game_rules(args, ctx):
    from realai.plugins.rackup_coach.games import game_knowledge, list_disciplines, normalize_discipline

    raw = str(args.get("discipline") or "")
    disc = normalize_discipline(raw, default="")
    k = game_knowledge(disc) if disc else None
    if not k:
        return {"ok": False, "error": "unknown discipline", "known": [d["display"] for d in list_disciplines()]}
    return {"ok": True, "id": k.get("id"), "display": k.get("display"), "objective": k.get("objective"),
            "rack": k.get("rack"), "key_rules": list(k.get("key_rules") or [])[:5], "fouls": list(k.get("fouls") or [])[:6]}


def coach_drill(args, ctx):
    rating = _num(args.get("rating"))
    if rating is None:
        return {"ok": False, "error": "need rating"}
    minutes = int(_num(args.get("minutes"), 30) or 30)
    r = _invoke("coach", {"id": "player", "rating": rating}, {"discipline": str(args.get("discipline") or "8-ball"),
                                                               "minutes": minutes})
    res = r.get("result") or {}
    plan = res.get("practice_plan") or {}
    if not r.get("ok", True) or not plan:
        return {"ok": False, "error": r.get("error") or "coach failed"}
    return {"ok": True, "discipline": res.get("discipline_display") or res.get("discipline"), "band_label": res.get("band_label"),
            "duration_minutes": plan.get("duration_minutes"), "focus": plan.get("band_message"),
            "blocks": [{"skill": b.get("skill"), "minutes": b.get("minutes"), "drill": b.get("drill")} for b in plan.get("blocks", [])][:6]}


def hall_context(args, ctx):
    ts = str(args.get("table_size") or "").lower().replace(" ", "").replace("foot", "ft").replace("'", "ft")
    if ts not in ("7ft", "9ft"):
        return {"ok": False, "error": "table_size must be 7ft or 9ft"}
    payload = {"hall": {"name": str(args.get("hall_name") or "")}, "session": {"table_size": ts}}
    if args.get("skill_level"):
        payload["session"]["skill_level"] = str(args["skill_level"])
        payload["skill_level"] = str(args["skill_level"])
    r = _invoke("hall_context", {"id": "player"}, payload)
    res = r.get("result") or {}
    py = res.get("pyramid") or {}
    if not r.get("ok", True) or not py:
        return {"ok": False, "error": r.get("error") or "hall_context failed"}
    return {"ok": True, "hall_name": res.get("hall_name") or None, "table_size": py.get("table_size"),
            "skill_level": py.get("skill_level"), "rack_size": py.get("rack_size"), "points_to_win": py.get("points_to_win"),
            "call_shot": py.get("call_shot"), "scoring": py.get("scoring"), "one_ball_value": py.get("one_ball_value")}


# ----------------------------------------------------------------------------- self-knowledge
def _rel(p: Any) -> Any:
    try:
        return Path(str(p)).resolve().relative_to(_ROOT).as_posix()
    except Exception:
        return p


def modules_index() -> List[Dict[str, Any]]:
    from abilities import core_surface, modules_surface

    out = [{"id": m.get("id"), "role": m.get("role"), "import": m.get("module"), "present": bool(m.get("present")),
            "path": _rel(m.get("path")), "pkg": "modules"} for m in modules_surface._inventory().get("modules") or []]
    for m in core_surface._inventory().get("modules") or []:
        out.append({"id": m.get("id"), "role": m.get("role"), "import": m.get("module") or m.get("import"),
                    "present": bool(m.get("present", True)), "path": _rel(m.get("path")), "pkg": "realai.core"})
    return [m for m in out if m.get("id")]


def plugins_index() -> List[Dict[str, Any]]:
    from abilities import plugins_surface

    from realai.plugin_registry import list_plugins

    reg = {str(p.get("name")): p for p in list_plugins() if isinstance(p, dict)}
    out = []
    for p in plugins_surface._inventory().get("live_plugins") or []:
        r = reg.pop(str(p.get("id")), {})
        out.append({"id": p.get("id"), "role": p.get("role"), "kind": p.get("kind"), "present": bool(p.get("present")),
                    "path": _rel(p.get("path")), "version": r.get("version"), "capabilities": r.get("capabilities") or []})
    for name, r in reg.items():
        out.append({"id": name, "role": None, "kind": "REGISTRY", "present": None, "path": None,
                    "version": r.get("version"), "capabilities": r.get("capabilities") or []})
    return out


def _rank(query, items, fields, k=3):
    from realai import hive_tools

    return hive_tools._rank(query, items, fields, k)


def module_lookup(args, ctx):
    hits = _rank(str(args.get("query", "")), modules_index(), ["id", "role", "import"], 3)
    return {"ok": bool(hits), "modules": hits} if hits else {"ok": False, "error": "no module matches",
                                                             "known": [m["id"] for m in modules_index()][:40]}


def plugin_lookup(args, ctx):
    hits = _rank(str(args.get("query", "")), plugins_index(), ["id", "role", "capabilities"], 3)
    return {"ok": bool(hits), "plugins": hits} if hits else {"ok": False, "error": "no plugin matches",
                                                             "known": [p["id"] for p in plugins_index()]}


def plugin_registry_list(args, ctx):
    from realai.plugin_registry import list_plugins

    ps = [{"name": p.get("name"), "version": p.get("version"), "capabilities": (p.get("capabilities") or [])[:8]}
          for p in list_plugins() if isinstance(p, dict)]
    return {"ok": True, "count": len(ps), "plugins": ps}


def organs_hive_status(args, ctx):
    from modules.organs.hive import hive_status

    h = hive_status()
    out = {"ok": True, "organ_count": h["organ_count"], "expected": h["expected"], "complete": h["complete"],
           "by_category": h["by_category"]}
    cat = str(args.get("category") or "").strip().lower()
    if cat:
        out["category"] = cat
        out["category_count"] = h["by_category"].get(cat, 0)
    return out


# ----------------------------------------------------------------------------- snapshot-backed stores
_SNAP: Dict[str, Path] = {}


def _home() -> Path:
    return Path(os.environ.get("REALAI_HOME") or _ROOT)


def snapshot(name: str, src: Path, ctx: Optional[Dict[str, Any]] = None) -> Optional[Path]:
    """Copy `src` once per process into a private temp dir; tools read only the copy."""
    if ctx and ctx.get(f"snapshot_{name}"):
        return Path(ctx[f"snapshot_{name}"])
    if name not in _SNAP:
        d = Path(tempfile.mkdtemp(prefix=f"realai-snap-{name}-"))
        dst = d / src.name
        if src.is_file():
            shutil.copy2(src, dst)
        _SNAP[name] = dst
    return _SNAP[name]


def memory_search(args, ctx):
    q = str(args.get("query", "")).strip()
    if not q:
        return {"ok": False, "error": "need query"}
    src = Path(os.environ.get("REALAI_MEMORY_DB") or _home() / "memory" / "hive" / "memory.sqlite3")
    snap = snapshot("memory", src, ctx)
    if not snap.is_file():
        return {"ok": True, "snapshot": "empty (no memory.sqlite3)", "namespace": str(args.get("namespace") or "default"),
                "hits": []}
    from agent_tools.engine.memory import SQLiteMemoryAdapter

    ns = str(args.get("namespace") or "default")
    hits = SQLiteMemoryAdapter(snap).search(ns, q, k=max(1, min(int(_num(args.get("k"), 5) or 5), 10)))
    return {"ok": True, "snapshot": "memory.sqlite3 copy", "namespace": ns,
            "hits": [{k: (str(v)[:300] if isinstance(v, str) else v) for k, v in (h.items() if isinstance(h, dict) else [("value", h)])}
                     for h in hits]}


def _load_approvals(path: Path) -> Dict[str, Any]:
    """Same parse as realai.plugins.tools.approval_store._load (that module imports core.security, which is
    not importable outside the server). Read-only: there is no write path here."""
    import json

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"items": []}


def approval_status(args, ctx):
    src = Path(os.environ.get("REALAI_APPROVALS_STORE") or os.environ.get("APPROVALS_STORE") or _home() / ".approvals.json")
    snap = snapshot("approvals", src, ctx)
    items = _load_approvals(snap).get("items", []) if snap.is_file() else []
    counts: Dict[str, int] = {}
    for it in items:
        counts[str(it.get("status"))] = counts.get(str(it.get("status")), 0) + 1
    want = str(args.get("status") or "pending").lower()
    sel = [{"id": it.get("id"), "action": it.get("action"), "status": it.get("status")} for it in items
           if str(it.get("status", "")).lower() == want][:10]
    return {"ok": True, "total": len(items), "by_status": counts, "status": want, "items": sel,
            "note": "read-only view; approving happens only in the approval UI by a human"}


EXECUTORS = {"rating_update_preview": rating_update_preview, "matchmaking_suggest": matchmaking_suggest,
             "rating_intel": rating_intel, "game_rules": game_rules, "coach_drill": coach_drill, "hall_context": hall_context,
             "module_lookup": module_lookup, "plugin_lookup": plugin_lookup, "plugin_registry_list": plugin_registry_list,
             "organs_hive_status": organs_hive_status, "memory_search": memory_search, "approval_status": approval_status}

# facts an answer must mention (verifier): result -> list of alternatives groups; each group needs one hit
def key_facts(name: str, r: Dict[str, Any], args: Dict[str, Any]) -> List[List[str]]:
    def num(x):
        if x is None:
            return []
        f = float(x)
        return [f"{f:.0f}", f"{f:.1f}", f"{f:.2f}", str(x)]
    if name == "rating_update_preview":
        return [num(r.get("rating_after")) + [str(r.get("display_after") or "")]]
    if name == "matchmaking_suggest":
        return [[str(r.get("best"))]] if r.get("best") else []
    if name == "rating_intel":
        return [[str(r.get("trajectory"))]] if r.get("trajectory") else []
    if name == "game_rules":
        return [[str(r.get("display")), str(r.get("id")).replace("_", " ")]]
    if name == "coach_drill":
        return [[str(b.get("drill"))[:25] for b in r.get("blocks") or []] + [str(b.get("skill")).replace("_", " ") for b in r.get("blocks") or []]]
    if name == "hall_context":
        return [num(r.get("points_to_win"))]
    if name in ("module_lookup", "plugin_lookup"):
        key = "modules" if name == "module_lookup" else "plugins"
        return [[str(m.get("id")) for m in r.get(key) or []] + [str(m.get("id")).replace("_", " ") for m in r.get(key) or []]]
    if name == "plugin_registry_list":
        return [[str(p.get("name")) for p in r.get("plugins") or []] + [str(r.get("count"))]]
    if name == "organs_hive_status":
        return [num(r.get("organ_count")) + num(r.get("category_count"))]
    if name == "approval_status":
        return [[str(r.get("total")), "no " + str(r.get("status")), "none", "no pending", "0"]]
    if name == "memory_search":
        return [] if r.get("hits") else [["no", "nothing", "empty", "0"]]
    return []
