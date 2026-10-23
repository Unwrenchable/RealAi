"""Hive team endpoints for the v3 orchestrator (:8001).

  GET  /v1/hive/teams                 -> teams (lead, members, ownership, handoffs)
  POST /v1/hive/teams/<id>/run        -> Overmind run {"goal": "..."}
  POST /v1/hive/playtest              -> playtest loop {"team": "vault77"}
  GET  /v1/hive/findings?team=&limit= -> recorded qa.finding events
  GET  /v1/hive/events                -> SSE live hive events (handler streams; see events.py)
  POST bodies may add {"async": true}: returns {"run_id"} at once, progress arrives on /v1/hive/events.

Every route sits behind the existing hive_guard (Host/Origin/body/rate checks) and, on top of
that, always requires loopback client + the local hive token, even when REALAI_HIVE_TOKEN_MODE
is off. Pure functions: the handler passes (method, path, query, body, client_ip, headers).
"""
from __future__ import annotations

import hmac
import re
import threading
import time
from typing import Any, Callable, Mapping

from .hive_client import LOOPBACK, local_token

PREFIXES = ("/v1/hive/teams", "/v1/hive/playtest", "/v1/hive/findings", "/v1/hive/events", "/v1/hive/runs")
SSE_PATH = "/v1/hive/events"
_RUNS: dict[str, Any] = {}
_RUN_LOCK = threading.Lock()
MAX_CONCURRENT_RUNS = 1
_RUN = re.compile(r"^/v1/hive/teams/([A-Za-z0-9_.-]{1,64})/run$")


def handles(path: str) -> bool:
    p = path.rstrip("/")
    return any(p == x or p.startswith(x + "/") for x in PREFIXES)


def _presented(headers: Mapping[str, str]) -> str:
    get = getattr(headers, "get", None)
    tok = (get("X-RealAI-Token") if get else "") or ""
    if not tok and get:
        auth = get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            tok = auth[7:]
    return tok.strip()


def authorize(client_ip: str, headers: Mapping[str, str], token_getter: Callable[[], str] = local_token) -> tuple[int, str] | None:
    if (client_ip or "") not in LOOPBACK and not str(client_ip).startswith("::ffff:127."):
        return 403, "loopback_only"
    want = token_getter()
    if not want:
        return 503, "no_local_token"
    got = _presented(headers)
    if not got or not hmac.compare_digest(got.encode("utf-8"), want.encode("utf-8")):
        return 401, "token_required"
    return None


def _team_dict(t: Any) -> dict[str, Any]:
    return {"id": t.id, "name": getattr(t, "name", t.id), "lead": t.lead, "members": list(t.members),
            "ownership": [vars(o) if hasattr(o, "__dict__") else o for o in t.ownership],
            "handoffs": list(getattr(t, "handoffs", []) or [])}


def handle(method: str, path: str, query: Mapping[str, list[str]] | None, body: dict[str, Any] | None,
           client_ip: str, headers: Mapping[str, str], token_getter: Callable[[], str] = local_token) -> tuple[int, dict[str, Any]]:
    denied = authorize(client_ip, headers, token_getter)
    if denied:
        return denied[0], {"error": denied[1]}
    p = path.rstrip("/")
    q = query or {}
    body = body or {}
    from .registry import load_registry
    from .teams import load_teams

    if method == "GET" and p == "/v1/hive/teams":
        teams = load_teams(load_registry())
        return 200, {"teams": [_team_dict(t) for t in teams.values()]}
    if method == "GET" and p == "/v1/hive/runs":
        with _RUN_LOCK:
            return 200, {"runs": dict(_RUNS)}
    if method == "GET" and p == "/v1/hive/findings":
        from .playtest import read_findings

        try:
            limit = int((q.get("limit") or ["100"])[0])
        except ValueError:
            limit = 100
        team = (q.get("team") or [None])[0]
        rows = read_findings(limit=min(max(limit, 1), 1000), team=team)
        return 200, {"findings": rows, "count": len(rows)}
    m = _RUN.match(p)
    if method == "POST" and m:
        goal = str(body.get("goal") or "").strip()
        if not goal:
            return 400, {"error": "goal_required"}
        from .overmind import Overmind

        reg = load_registry()
        om = Overmind(registry=reg, teams=load_teams(reg))
        if m.group(1) not in (om.teams or {}):
            return 404, {"error": "unknown_team"}
        if body.get("async"):
            return _spawn(lambda rid: om.run(goal[:4000], team_id=m.group(1), run_id=rid), "run")
        return 200, om.run(goal[:4000], team_id=m.group(1))
    if method == "POST" and p == "/v1/hive/playtest":
        from .playtest import PlaytestLoop

        teams = load_teams(load_registry())
        team = teams.get(str(body.get("team") or "vault77"))
        if not team:
            return 404, {"error": "unknown_team"}
        qa = str(body.get("qa_agent") or "game-qa-lead")
        if body.get("async"):
            return _spawn(lambda rid: PlaytestLoop(team, qa_agent=qa, run_id=rid).run(), "pt")
        return 200, PlaytestLoop(team, qa_agent=qa).run()
    return 404, {"error": "not_found"}


def _spawn(fn: Callable[[str], Any], prefix: str) -> tuple[int, dict[str, Any]]:
    """One background run at a time (local GPU); events stream its progress."""
    from . import events

    with _RUN_LOCK:
        if sum(1 for r in _RUNS.values() if r["status"] == "running") >= MAX_CONCURRENT_RUNS:
            return 409, {"error": "run_in_progress"}
        rid = f"{prefix}-{int(time.time() * 1000)}"
        _RUNS[rid] = {"status": "running", "started": time.time()}

    def _work() -> None:
        try:
            fn(rid)
            status = "done"
        except Exception as e:  # noqa: BLE001
            events.emit("run.error", run=rid, error=type(e).__name__)
            status = "error"
        with _RUN_LOCK:
            _RUNS[rid]["status"] = status

    threading.Thread(target=_work, name=f"hive-{rid}", daemon=True).start()
    return 202, {"run_id": rid, "events": SSE_PATH}
