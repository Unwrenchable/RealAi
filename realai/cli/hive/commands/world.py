"""World / Universe Mode inspection — Hive CLI surface."""
from __future__ import annotations

from pathlib import Path

import click

from realai.cli.hive import world_inspector
from realai.cli.hive.format import emit_json, error, truncate


def _ws(ctx) -> Path:
    return Path(getattr(ctx, "workspace", None) or r"C:\RealAI-clean")


@click.group("world")
def world_group():
    """Universe Mode status + registry, doctor, architect, graph."""


@world_group.command("status")
@click.pass_obj
def world_status(ctx):
    """Show Universe Mode ON/OFF and subsystem summary."""
    try:
        from realai.universe import universe_status
    except Exception as e:
        error("universe status failed", detail=str(e))
        raise SystemExit(1)
    data = universe_status(_ws(ctx))
    if ctx.as_json:
        emit_json(data)
        return
    click.echo(f"universe: {data.get('universe')}")
    click.echo(f"workspace: {data.get('workspace')}")
    click.echo(f"worlds: {data.get('worlds')}")
    click.echo(f"entities: {data.get('entities')} ({data.get('entity_count')})")
    click.echo(f"memory: {data.get('memory')}")
    subs = data.get("subsystems") or {}
    click.echo("subsystems:")
    for name, body in subs.items():
        if isinstance(body, dict):
            click.echo(f"  {name}: ok={body.get('ok', True)} active={body.get('active', body.get('present', ''))}")
        else:
            click.echo(f"  {name}: {body}")


@world_group.command("doctor")
@click.pass_obj
def world_doctor(ctx):
    """Universal Doctor — read-only checks (no heal)."""
    from realai.universe.doctor import diagnose

    data = diagnose(_ws(ctx))
    if ctx.as_json:
        emit_json(data)
        return
    click.echo(f"universal_doctor: {'OK' if data.get('ok') else 'ISSUES'}")
    for name, row in (data.get("checks") or {}).items():
        mark = "OK" if row.get("ok") else "!!"
        click.echo(f"  [{mark}] {name}  {row.get('detail')}")
    if data.get("failed"):
        click.echo(f"failed: {', '.join(data['failed'])}")


@world_group.command("architect")
@click.pass_obj
def world_architect(ctx):
    """Universal Architect — structural survey."""
    from realai.universe.architect import survey

    data = survey(_ws(ctx))
    if ctx.as_json:
        emit_json(data)
        return
    click.echo(f"universal_architect: {data.get('workspace')}")
    hier = (data.get("hierarchy") or {}).get("layers") or []
    click.echo(f"hierarchy: {' → '.join(hier)}")
    click.echo(f"worlds: {len(data.get('worlds') or [])}")
    for row in data.get("layout") or []:
        mark = "OK" if row.get("exists") else "--"
        click.echo(f"  [{mark}] {row.get('name')}")


@world_group.command("registry")
@click.pass_obj
def world_registry(ctx):
    """Universal Registry counts + sample entities."""
    from realai.universe.registry import build_registry

    data = build_registry(_ws(ctx))
    if ctx.as_json:
        emit_json(data)
        return
    counts = data.get("counts") or {}
    click.echo(f"registry: entities={counts.get('entities')} environments={counts.get('environments')} interactions={counts.get('interactions')}")
    for e in (data.get("entities") or [])[:12]:
        click.echo(f"  {e.get('type')}: {e.get('id')}")


@world_group.command("graph")
@click.pass_obj
def world_graph(ctx):
    """Cross-world knowledge graph summary."""
    from realai.universe.knowledge_graph import build_graph

    data = build_graph(_ws(ctx))
    if ctx.as_json:
        emit_json(data)
        return
    click.echo(f"knowledge_graph: nodes={data.get('node_count')} edges={data.get('edge_count')}")
    for n in data.get("nodes") or []:
        click.echo(f"  {n.get('id')}: {n.get('label')} ({n.get('kind')})")


@world_group.command("route")
@click.argument("task", nargs=-1, required=True)
@click.option("--world", "world_id", default="world-0")
@click.pass_obj
def world_route(ctx, task, world_id):
    """Universal Agent Dispatcher — suggest hive agent for a task."""
    from realai.universe.dispatcher import route

    data = route(" ".join(task), world_id=world_id)
    if ctx.as_json:
        emit_json(data)
        return
    click.echo(f"agent: {data.get('agent_id')}  world: {data.get('world_id')}")
    click.echo(f"reason: {data.get('reason')}")


@world_group.command("show")
@click.pass_obj
def world_show(ctx):
    payload = world_inspector.load_world(_ws(ctx))
    if not payload.get("ok"):
        error("world show failed", detail=payload.get("error"))
        raise SystemExit(1)
    summary = world_inspector.summarize(payload)
    if ctx.as_json:
        emit_json({"summary": summary, "payload": payload})
        return
    click.echo(f"source: {summary.get('source')}")
    if "key_count" in summary:
        click.echo(f"keys ({summary['key_count']}): {', '.join(summary.get('keys') or [])}")
        sample = summary.get("sample") or {}
        for k, v in sample.items():
            click.echo(f"  {k}: {truncate(str(v), 120)}")
    else:
        click.echo(truncate(str(summary.get("preview")), 500))


@world_group.command("query")
@click.argument("query", nargs=-1, required=True)
@click.pass_obj
def world_query(ctx, query):
    """Key/substring search over world-model data."""
    q = " ".join(query).strip()
    payload = world_inspector.load_world(_ws(ctx))
    if not payload.get("ok"):
        error("world query failed", detail=payload.get("error"))
        raise SystemExit(1)
    hits = world_inspector.query_world(payload, q)
    if ctx.as_json:
        emit_json(hits)
        return
    if not hits.get("hits"):
        click.echo("(no hits)")
        return
    for h in hits["hits"]:
        click.echo(f"{h['key']}: {truncate(str(h['value']), 200)}")