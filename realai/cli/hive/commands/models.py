"""models / providers commands."""
from __future__ import annotations

import click

from realai.cli.hive.format import emit_json, error, table, truncate


@click.command("models")
@click.option("--limit", default=30, show_default=True, help="Max rows to print")
@click.pass_obj
def models_cmd(ctx, limit):
    """List RealAI model catalog (orchestrator facade)."""
    try:
        data = ctx.client.models()
    except Exception as e:
        error("failed to list models", hint="realai stack up", detail=str(e))
        raise SystemExit(1)
    if ctx.as_json:
        emit_json(data)
        return
    rows = []
    for m in (data.get("data") or [])[: max(1, limit)]:
        meta = m.get("realai") or {}
        rows.append(
            [
                m.get("id"),
                meta.get("family") or "",
                "yes" if meta.get("loaded_now") else "no",
                truncate(meta.get("gguf_filename") or meta.get("backend_model_id") or "", 40),
            ]
        )
    click.echo(table(rows, headers=["id", "family", "loaded", "backend"]))
    realai = data.get("realai") or {}
    if realai.get("default_model"):
        click.echo(f"\ndefault: {realai.get('default_model')}  vulkan={realai.get('vulkan_base')}")


@click.command("providers")
@click.pass_obj
def providers_cmd(ctx):
    """List inference providers."""
    try:
        data = ctx.client.providers()
    except Exception as e:
        error("failed to list providers", hint="realai stack up", detail=str(e))
        raise SystemExit(1)
    if ctx.as_json:
        emit_json(data)
        return
    rows = []
    for p in data.get("data") or []:
        rows.append(
            [
                p.get("id"),
                "on" if p.get("enabled") else "off",
                p.get("type") or "",
                truncate(p.get("api_base") or "", 40),
                (p.get("health") or {}).get("status") or "",
            ]
        )
    click.echo(table(rows, headers=["id", "enabled", "type", "api_base", "health"]))
