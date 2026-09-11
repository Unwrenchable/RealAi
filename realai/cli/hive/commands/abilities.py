"""Ability catalog + runner — uses ability_runner module."""
from __future__ import annotations

import click

from realai.cli.hive import ability_runner
from realai.cli.hive.format import emit_json, error, table


@click.group("abilities", invoke_without_command=True)
@click.option("--live", is_flag=True, help="Only LIVE abilities")
@click.pass_context
def abilities_group(ctx, live):
    """Ability catalog from orchestrator honesty coverage."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(abilities_list, live=live)


@abilities_group.command("list")
@click.option("--live", is_flag=True)
@click.pass_obj
def abilities_list(ctx, live):
    try:
        data = ability_runner.catalog(ctx.client, live_only=live)
    except Exception as e:
        error("abilities failed", hint="realai stack up", detail=str(e))
        raise SystemExit(1)
    if ctx.as_json:
        emit_json(data)
        return
    rows = [[str(c), ""] for c in (data.get("capabilities") or [])[:80]]
    click.echo(table(rows, headers=["capability", "note"]) or "(none)")
    cov = data.get("by_status") or {}
    if cov:
        click.echo(f"\nby_status: {cov}  weighted_pct={data.get('weighted_pct')}")


@click.group("ability")
def ability_group():
    """Run a named ability via tools/execute."""


@ability_group.command("run")
@click.argument("name")
@click.option("--input", "input_text", default="", help="Natural-language input")
@click.pass_obj
def ability_run(ctx, name, input_text):
    try:
        result = ability_runner.run_ability(ctx.client, name, input_text=input_text)
    except Exception as e:
        error("ability run failed", detail=str(e))
        raise SystemExit(1)
    if ctx.as_json or True:
        # abilities often return structured payloads — always JSON-friendly
        emit_json(result)
