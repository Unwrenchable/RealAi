"""Knowledge synthesis — knowledge graph + world model planning."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "knowledge_synthesis",
    "name": "knowledge_synthesis",
    "type": "ability",
    "status": "LIVE",
    "source": "realai.knowledge_graph + realai.world_model",
    "dest": "abilities/knowledge_synthesis.py",
    "capabilities": ["knowledge_graph", "synthesis", "world_model", "goals"],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    from realai.knowledge_graph import (
        KNOWLEDGE_GRAPH,
        Entity,
        Relationship,
        SynthesisEngine,
    )
    from realai.world_model import GOAL_TRACKER, PLANNING_ENGINE, WORLD_STATE

    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or "synthesize").lower()
    query = str(ctx.get("query") or input or "").strip()

    if action in {"add", "add_entity"}:
        name = str(ctx.get("name") or query or "entity")
        eid = str(ctx.get("entity_id") or f"e-{name.lower().replace(' ', '-')[:40]}")
        etype = str(ctx.get("entity_type") or ctx.get("type") or "concept")
        KNOWLEDGE_GRAPH.add_entity(Entity(eid, name, etype, dict(ctx.get("attributes") or {})))
        return {"ok": True, "ability": "knowledge_synthesis", "action": "add_entity", "entity_id": eid}

    if action in {"relate", "add_relationship"}:
        subj = str(ctx.get("subject_id") or "")
        pred = str(ctx.get("predicate") or "related_to")
        obj = str(ctx.get("object_id") or "")
        if not (subj and obj):
            return {"ok": False, "error": "subject_id_and_object_id_required", "ability": "knowledge_synthesis"}
        rid = str(ctx.get("relationship_id") or f"r-{subj}-{pred}-{obj}")[:80]
        KNOWLEDGE_GRAPH.add_relationship(Relationship(rid, subj, pred, obj))
        return {"ok": True, "ability": "knowledge_synthesis", "action": "add_relationship", "id": rid}

    if action in {"goal", "add_goal"}:
        goal = GOAL_TRACKER.add_goal(query or str(ctx.get("goal") or "untitled"))
        plan = PLANNING_ENGINE.plan(goal.description, WORLD_STATE, max_steps=int(ctx.get("max_steps") or 3))
        return {
            "ok": True,
            "ability": "knowledge_synthesis",
            "action": "goal",
            "goal": {"id": goal.id, "description": goal.description, "status": goal.status},
            "plan": plan,
            "world_stats": getattr(WORLD_STATE, "summary", lambda: {})()
            if callable(getattr(WORLD_STATE, "summary", None))
            else {"type": type(WORLD_STATE).__name__},
        }

    # default: synthesize answer + graph stats
    engine = SynthesisEngine()
    if query:
        # seed a lightweight entity from the query tokens if graph empty
        if KNOWLEDGE_GRAPH.stats().get("entities", 0) == 0 and query:
            KNOWLEDGE_GRAPH.add_entity(Entity("seed-realai", "RealAI", "system", {"note": "auto-seed"}))
        ans = engine.answer(query, KNOWLEDGE_GRAPH, max_hops=int(ctx.get("max_hops") or 2))
    else:
        ans = {"synthesis": "Provide a query to synthesize.", "entities_found": [], "relationships": []}

    return {
        "ok": True,
        "ability": "knowledge_synthesis",
        "action": "synthesize",
        "query": query,
        "answer": ans,
        "graph_stats": KNOWLEDGE_GRAPH.stats(),
        "goals_tracked": len(GOAL_TRACKER.list_goals() or []),
    }
