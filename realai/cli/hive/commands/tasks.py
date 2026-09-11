"""task create / list / get."""
from __future__ import annotations

import click

from realai.cli.hive.format import emit_json, error, table, truncate


@click.group("task")
def task_group():
    """Multi-step orchestrator tasks (/v1/tasks)."""


@task_group.command("list")
@click.pass_obj
def task_list(ctx):
    try:
        data = ctx.client.list_tasks()
    except Exception as e:
        error("task list failed", hint="realai stack up", detail=str(e))
        raise SystemExit(1)
    if ctx.as_json:
        emit_json(data)
        return
    rows = []
    for t in data.get("data") or []:
        rows.append(
            [
                t.get("id"),
                t.get("status"),
                truncate(t.get("task") or "", 60),
            ]
        )
    click.echo(table(rows, headers=["id", "status", "task"]) or "(no tasks)")


@task_group.command("get")
@click.argument("task_id")
@click.pass_obj
def task_get(ctx, task_id):
    try:
        data = ctx.client.get_task(task_id)
    except Exception as e:
        error("task get failed", detail=str(e))
        raise SystemExit(1)
    emit_json(data) if ctx.as_json else emit_json(data)


@task_group.command("create")
@click.argument("task", nargs=-1, required=True)
@click.option("--context", default="", help="Optional context string")
@click.pass_obj
def task_create(ctx, task, context):
    text = " ".join(task).strip()
    try:
        data = ctx.client.create_task(text, context=context)
    except Exception as e:
        error("task create failed", hint="realai stack up", detail=str(e))
        raise SystemExit(1)
    if ctx.as_json:
        emit_json(data)
    else:
        click.echo(f"created {data.get('id') or data}")
