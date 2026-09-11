"""Agent router commands — RealAI-native task→agent mapping."""
from __future__ import annotations

import click

from realai.cli.hive import agent_router
from realai.cli.hive.format import emit_json, error, kv, table


@click.command("route")
@click.argument("task", nargs=-1, required=True)
@click.option("--agent", "agent_id", default=None, help="Force agent id")
@click.option("--execute", "-x", is_flag=True, help="Execute via orch chat after routing")
@click.option("--multi", is_flag=True, help="Execute as multi-agent pipeline")
@click.option("--model", default="realai-default-coder")
@click.option("--max-tokens", default=384, type=int)
@click.pass_obj
def route_cmd(ctx, task, agent_id, execute, multi, model, max_tokens):
    """
    Route a task to a hive agent (or execute it).

    \b
      realai route "refactor ensure_gpu_server"
      realai route -x "refactor ensure_gpu_server"
      realai route --multi "surface scan the hive"
      realai routes                 # show routing table
    """
    text = " ".join(task).strip()
    roster = agent_router.list_roster(ctx.client if execute or multi else None)
    decision = (
        agent_router.RouteDecision(agent_id, "user override", 1.0, source="override")
        if agent_id
        else agent_router.route_task(text, roster=roster.get("agents"))
    )

    if not execute and not multi:
        payload = {"task": text, "route": decision.__dict__, "roster_source": roster.get("source")}
        if ctx.as_json:
            emit_json(payload)
            return
        click.echo(kv("task", text))
        click.echo(kv("agent", decision.agent_id))
        click.echo(kv("confidence", f"{decision.confidence:.2f}"))
        click.echo(kv("reason", decision.reason))
        if decision.alternates:
            click.echo(kv("alts", ", ".join(decision.alternates)))
        click.echo("hint: add -x to execute, or --multi for pipeline")
        return

    try:
        result = agent_router.run_routed(
            ctx.client,
            text,
            agent_id=decision.agent_id,
            model=model,
            max_tokens=max_tokens,
            use_multi=multi,
        )
    except Exception as e:
        error("route execute failed", hint="realai stack up", detail=str(e))
        raise SystemExit(1)

    if ctx.as_json:
        emit_json(result)
        return
    click.echo(kv("agent", result.get("route", {}).get("agent_id")))
    click.echo(kv("mode", result.get("mode")))
    if result.get("mode") == "multi":
        ma = result.get("result") or {}
        click.echo(kv("ok", ma.get("ok")))
        stages = ma.get("stage_outputs") or {}
        for name in ("planner", "worker", "critic"):
            body = stages.get(name) or ma.get(name) or ""
            if body:
                click.echo(f"\n## {name}\n{body[:1200]}")
    else:
        click.echo(result.get("content") or "")


@click.command("routes")
@click.pass_obj
def routes_cmd(ctx):
    """Show keyword → archetype routing table."""
    rows = [(aid, ", ".join(keys[:6])) for aid, keys in agent_router._ROUTE_TABLE]
    if ctx.as_json:
        emit_json({"routes": [{"agent": a, "keywords": k} for a, k in rows]})
        return
    click.echo(table([[a, k] for a, k in rows], headers=["agent", "keywords (sample)"]))
