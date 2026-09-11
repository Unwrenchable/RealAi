"""multi-agent pipeline command."""
from __future__ import annotations

import click

from realai.cli.hive.format import emit_json, error, section, truncate


@click.command("multi")
@click.argument("task", nargs=-1, required=True)
@click.option("--mode", type=click.Choice(["pipeline", "parallel"]), default="pipeline")
@click.option("--max-tokens", default=384, type=int)
@click.option("--temperature", default=0.3, type=float)
@click.pass_obj
def multi_cmd(ctx, task, mode, max_tokens, temperature):
    """Run planner→worker→critic (or parallel) via orchestrator."""
    text = " ".join(task).strip()
    try:
        result = ctx.client.multi_agent(
            text, mode=mode, max_tokens=max_tokens, temperature=temperature
        )
    except Exception as e:
        error("multi-agent failed", hint="realai stack up", detail=str(e))
        raise SystemExit(1)
    if ctx.as_json:
        emit_json(result)
        return
    if not result.get("ok"):
        error(
            result.get("error") or "pipeline failed",
            hint=result.get("hint") or "realai stack up",
            detail=str(result.get("binding") or "")[:300],
        )
        raise SystemExit(1)
    click.echo(f"ok  mode={result.get('mode')}  duration_ms={result.get('duration_ms')}")
    stages = result.get("stage_outputs") or {}
    for name in ("planner", "worker", "critic"):
        body = stages.get(name) or result.get(name) or ""
        click.echo(section(name.upper()))
        click.echo(body if len(body) < 2000 else body[:2000] + "\n…")
