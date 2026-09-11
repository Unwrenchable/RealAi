"""
RealAI Hive agent router — maps tasks → archetype / agentx id → execution path.

Not a chat REPL. Routes through orchestrator when up; falls back to local roster.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Keyword → preferred hive archetype (order matters: first match wins within group)
_ROUTE_TABLE: List[Tuple[str, Tuple[str, ...]]] = [
    ("coder", ("code", "implement", "refactor", "patch", "debug", "fix", "python", "typescript", "compile")),
    ("architect", ("architect", "design", "structure", "module layout", "system design", "api design")),
    ("analyst", ("analy", "review", "critique", "summar", "compare", "evaluate")),
    ("memory", ("remember", "recall", "memory", "world model", "knowledge graph", "embed")),
    ("governor", ("policy", "safety", "guard", "approve", "risk", "compliance")),
    ("guardian", ("guardian", "secure", "threat", "harden")),
    ("router", ("route", "dispatch", "backend", "which model", "where to send")),
    ("planner", ("plan", "decompose", "steps", "roadmap", "break down")),
    ("executor", ("execute", "run task", "do the work", "carry out")),
    ("self-heal", ("self-heal", "self heal", "repair", "promote", "assemble", "discover gold")),
    ("hive-orchestrator", ("orchestrat", "coordinate agents", "multi-agent", "swarm")),
    ("overseer", ("oversee", "coordinate", "supervise", "status of hive", "overall")),
]


@dataclass
class RouteDecision:
    agent_id: str
    reason: str
    confidence: float
    alternates: List[str] = field(default_factory=list)
    source: str = "keyword"


def list_roster(client=None, *, hive_only: bool = False, limit: int = 200) -> Dict[str, Any]:
    """Load merged agent roster via orch tool or local bridge."""
    if client is not None:
        try:
            raw = client.tool_execute("list_agents", {"limit": limit})
            res = raw.get("result") if isinstance(raw, dict) else raw
            if isinstance(res, dict) and res.get("agents") is not None:
                agents = list(res.get("agents") or [])
                if hive_only:
                    agents = [a for a in agents if a.get("hive") or a.get("source") == "github_agents"]
                return {
                    "ok": True,
                    "count": len(agents),
                    "agents": agents,
                    "hive": res.get("hive"),
                    "source": "orchestrator",
                }
        except Exception as e:
            local_err = str(e)
    else:
        local_err = None

    try:
        from realai.v3_runtime_bridge import hive_agents_status, list_agent_tools_agents

        data = list_agent_tools_agents(limit=limit, query="")
        agents = list(data.get("agents") or [])
        if hive_only:
            agents = [a for a in agents if a.get("hive") or a.get("source") == "github_agents"]
        return {
            "ok": True,
            "count": len(agents),
            "agents": agents,
            "hive": data.get("hive") or hive_agents_status(),
            "source": "local_bridge",
            "note": local_err,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "prior": local_err, "agents": [], "count": 0}


def route_task(task: str, *, roster: Optional[List[Dict[str, Any]]] = None) -> RouteDecision:
    """Choose best agent id for a natural-language task."""
    text = (task or "").strip().lower()
    if not text:
        return RouteDecision("overseer", "empty task → overseer", 0.2)

    scored: List[Tuple[float, str, str]] = []
    for agent_id, keys in _ROUTE_TABLE:
        hits = sum(1 for k in keys if k in text)
        if hits:
            conf = min(0.95, 0.45 + 0.15 * hits)
            scored.append((conf, agent_id, f"matched {hits} keyword(s) for {agent_id}"))

    # Prefer explicit agent id mention
    ids = {a.get("id") for a in (roster or []) if isinstance(a, dict)}
    for aid in ids:
        if aid and re.search(rf"\b{re.escape(str(aid).lower())}\b", text):
            return RouteDecision(str(aid), f"explicit mention of {aid}", 0.99, source="explicit")

    if not scored:
        return RouteDecision("overseer", "no keyword match → overseer", 0.35, alternates=["planner", "analyst"])

    scored.sort(key=lambda x: -x[0])
    best = scored[0]
    alts = [s[1] for s in scored[1:4]]
    return RouteDecision(best[1], best[2], best[0], alternates=alts, source="keyword")


def run_routed(
    client,
    task: str,
    *,
    agent_id: Optional[str] = None,
    model: str = "realai-default-coder",
    max_tokens: int = 512,
    use_multi: bool = False,
) -> Dict[str, Any]:
    """
    Execute a routed task.
    - use_multi: planner→worker→critic pipeline
    - else: single chat with agent_id injected
    """
    roster_data = list_roster(client, hive_only=False)
    decision = (
        RouteDecision(agent_id, "user override", 1.0, source="override")
        if agent_id
        else route_task(task, roster=roster_data.get("agents"))
    )

    if use_multi:
        result = client.multi_agent(task, mode="pipeline", max_tokens=max_tokens)
        return {
            "ok": bool(result.get("ok")),
            "mode": "multi",
            "route": decision.__dict__,
            "result": result,
        }

    resp = client.chat_completion(
        [{"role": "user", "content": task}],
        model=model,
        max_tokens=max_tokens,
        agent_id=decision.agent_id,
    )
    content = ((resp.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    return {
        "ok": True,
        "mode": "agent",
        "route": decision.__dict__,
        "content": content,
        "raw": resp,
    }
