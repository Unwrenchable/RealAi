"""agents list / info / run."""
from __future__ import annotations

import click

from realai.cli.hive.format import emit_json, error, table, truncate


def _list_agents(ctx, limit: int = 200, query: str = ""):
    try:
        raw = ctx.client.tool_execute(
            "list_agents",
            {"limit": limit, "query": query},
        )
    except Exception as e:
        # local fallback
        try:
            from realai.v3_runtime_bridge import list_agent_tools_agents

            return list_agent_tools_agents(limit=limit, query=query)
        except Exception as e2:
            raise RuntimeError(f"{e}; fallback: {e2}") from e
    res = raw.get("result") if isinstance(raw, dict) else raw
    if isinstance(res, dict) and "agents" in res:
        return res
    if isinstance(raw, dict) and "agents" in raw:
        return raw
    return {"count": 0, "agents": [], "raw": raw}


@click.group("agents", invoke_without_command=True)
@click.option("--hive", "hive_only", is_flag=True, help="Only hive archetypes")
@click.option("--query", "-q", default="", help="Filter by id/role/tags")
@click.option("--limit", default=50, show_default=True)
@click.pass_context
def agents_group(ctx, hive_only, query, limit):
    """Hive / agentx agent roster (default: list)."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(agents_list, hive_only=hive_only, query=query, limit=limit)


@agents_group.command("list")
@click.option("--hive", "hive_only", is_flag=True, help="Only hive archetypes")
@click.option("--query", "-q", default="", help="Filter by id/role/tags")
@click.option("--limit", default=50, show_default=True)
@click.pass_obj
def agents_list(ctx, hive_only, query, limit):
    """List discoverable agents."""
    try:
        data = _list_agents(ctx, limit=200 if hive_only else limit, query=query)
    except Exception as e:
        error("agents list failed", hint="realai stack up", detail=str(e))
        raise SystemExit(1)
    agents = list(data.get("agents") or [])
    if hive_only:
        agents = [a for a in agents if a.get("hive") or a.get("source") == "github_agents"]
    agents = agents[: max(1, limit)]
    if ctx.as_json:
        emit_json({"count": len(agents), "agents": agents, "hive": data.get("hive")})
        return
    rows = [
        [
            a.get("id"),
            truncate(a.get("role") or "", 36),
            a.get("risk") or a.get("risk_level") or "",
            "yes" if a.get("hive") else "",
            a.get("source") or "",
        ]
        for a in agents
    ]
    click.echo(table(rows, headers=["id", "role", "risk", "hive", "source"]))
    hive = data.get("hive") or {}
    if hive:
        click.echo(
            f"\nhive_mode={hive.get('mode')} present={hive.get('present')} missing={hive.get('missing')}"
        )


@agents_group.command("info")
@click.argument("agent_id")
@click.pass_obj
def agents_info(ctx, agent_id):
    """Show one agent definition."""
    try:
        raw = ctx.client.tool_execute("agent_info", {"agent_id": agent_id})
        res = raw.get("result") if isinstance(raw, dict) else raw
    except Exception as e:
        error("agent_info failed", detail=str(e))
        raise SystemExit(1)
    if ctx.as_json:
        emit_json(res)
        return
    agent = (res or {}).get("agent") if isinstance(res, dict) else None
    if not agent:
        error("agent not found", detail=agent_id)
        raise SystemExit(1)
    for k in ("id", "role", "description", "risk_level", "preferred_model", "hive", "tags", "capabilities"):
        if k in agent:
            click.echo(f"{k}: {agent.get(k)}")


@agents_group.command("run")
@click.argument("agent_id")
@click.argument("task", nargs=-1, required=True)
@click.option("--model", default="realai-default-coder")
@click.option("--max-tokens", default=384, type=int)
@click.pass_obj
def agents_run(ctx, agent_id, task, model, max_tokens):
    """Run a task as a named agent via orchestrator chat."""
    prompt = " ".join(task).strip()
    try:
        resp = ctx.client.chat_completion(
            [{"role": "user", "content": prompt}],
            model=model,
            max_tokens=max_tokens,
            agent_id=agent_id,
        )
    except Exception as e:
        error("agent run failed", hint="realai stack up", detail=str(e))
        raise SystemExit(1)
    if ctx.as_json:
        emit_json(resp)
        return
    content = ((resp.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    click.echo(content)
