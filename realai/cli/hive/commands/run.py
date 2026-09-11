"""Unified Hive runner — route+execute or multi-agent in one verb."""
from __future__ import annotations

import click

from realai.cli.hive import agent_router
from realai.cli.hive.format import emit_json, error, kv, section


@click.command("run")
@click.argument("task", nargs=-1, required=True)
@click.option("--agent", "agent_id", default=None, help="Pin agent id")
@click.option("--multi/--no-multi", default=True, help="Use multi-agent pipeline (default ON)")
@click.option("--model", default="realai-default-coder")
@click.option("--max-tokens", default=384, type=int)
@click.pass_obj
def run_cmd(ctx, task, agent_id, multi, model, max_tokens):
    """
    Execute a hive task (default: multi-agent pipeline).

    \b
      realai run "verify vulkan + orch health"
      realai run --no-multi --agent coder "fix banner.py"
    """
    text = " ".join(task).strip()
    try:
        result = agent_router.run_routed(
            ctx.client,
            text,
            agent_id=agent_id,
            model=model,
            max_tokens=max_tokens,
            use_multi=multi,
        )
    except Exception as e:
        error("run failed", hint="realai stack up", detail=str(e))
        raise SystemExit(1)

    if ctx.as_json:
        emit_json(result)
        return

    route = result.get("route") or {}
    click.echo(kv("route", f"{route.get('agent_id')}  conf={route.get('confidence')}  {route.get('reason')}"))
    click.echo(kv("mode", result.get("mode")))

    if result.get("mode") == "multi":
        ma = result.get("result") or {}
        if not ma.get("ok"):
            error(ma.get("error") or "pipeline failed", detail=str(ma.get("binding") or "")[:300])
            raise SystemExit(1)
        click.echo(kv("duration_ms", ma.get("duration_ms")))
        stages = ma.get("stage_outputs") or {}
        for name in ("planner", "worker", "critic"):
            body = stages.get(name) or ma.get(name) or ""
            click.echo(section(name.upper()))
            click.echo(body if len(body) < 2000 else body[:2000] + "\n…")
    else:
        click.echo(section("OUTPUT"))
        click.echo(result.get("content") or "")
