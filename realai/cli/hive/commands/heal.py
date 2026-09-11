"""self-heal commands."""
from __future__ import annotations

import click

from realai.cli.hive.format import emit_json, error, kv


@click.group("heal")
def heal_group():
    """Self-heal engine (discover / assemble / promote / cycle)."""


@heal_group.command("status")
@click.pass_obj
def heal_status(ctx):
    try:
        data = ctx.client.self_heal_status()
    except Exception as e:
        error("heal status failed", hint="realai stack up", detail=str(e))
        raise SystemExit(1)
    if ctx.as_json:
        emit_json(data)
        return
    click.echo(kv("enabled", data.get("enabled")))
    click.echo(kv("root", data.get("root")))
    cov = (data.get("ability_coverage") or {}).get("coverage") or data.get("ability_coverage") or {}
    if isinstance(cov, dict):
        click.echo(kv("abilities", f"{cov.get('live_count')}/{cov.get('ability_count')} LIVE  weighted={cov.get('weighted_pct')}"))
    arts = data.get("artifacts") or {}
    missing = [k for k, v in arts.items() if v is False]
    if missing:
        click.echo(kv("missing_artifacts", ", ".join(missing[:12])))
    click.echo(kv("promote_queue", data.get("promote_queue_items")))


@heal_group.command("cycle")
@click.pass_obj
def heal_cycle(ctx):
    """Run self-heal cycle endpoint if available."""
    try:
        data = ctx.client.self_heal_post("cycle")
    except Exception as e:
        error("heal cycle failed", detail=str(e))
        raise SystemExit(1)
    emit_json(data)


@heal_group.command("assemble")
@click.pass_obj
def heal_assemble(ctx):
    try:
        data = ctx.client.self_heal_post("assemble")
    except Exception as e:
        error("heal assemble failed", detail=str(e))
        raise SystemExit(1)
    emit_json(data)


@heal_group.command("promote")
@click.option("--dry-run", is_flag=True, default=True, help="Preview only (default)")
@click.option("--apply", is_flag=True, help="Apply promote (disables dry-run)")
@click.pass_obj
def heal_promote(ctx, dry_run, apply):
    body = {"dry_run": not apply}
    try:
        data = ctx.client.self_heal_post("promote", body)
    except Exception as e:
        error("heal promote failed", detail=str(e))
        raise SystemExit(1)
    emit_json(data)
