"""tools list / exec."""
from __future__ import annotations

import json

import click

from realai.cli.hive.format import emit_json, error, table, truncate


@click.group("tools", invoke_without_command=True)
@click.pass_context
def tools_group(ctx):
    """Orchestrator tool catalog."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(tools_list)


@tools_group.command("list")
@click.pass_obj
def tools_list(ctx):
    try:
        data = ctx.client.tools()
    except Exception as e:
        error("tools list failed", hint="realai stack up", detail=str(e))
        raise SystemExit(1)
    if ctx.as_json:
        emit_json(data)
        return
    rows = []
    for t in data.get("tools") or []:
        fn = (t.get("function") or {}) if isinstance(t, dict) else {}
        rows.append(
            [
                fn.get("name") or t.get("name") or "",
                truncate(fn.get("description") or t.get("description") or "", 70),
            ]
        )
    click.echo(table(rows, headers=["name", "description"]) or "(none)")


@click.group("tool")
def tool_group():
    """Execute a single orchestrator tool."""


@tool_group.command("exec")
@click.argument("name")
@click.option("--arg", "args", multiple=True, help="k=v argument (repeatable)")
@click.option("--json-args", default="", help="JSON object of arguments")
@click.pass_obj
def tool_exec(ctx, name, args, json_args):
    arguments = {}
    if json_args:
        arguments.update(json.loads(json_args))
    for item in args:
        if "=" not in item:
            error("bad --arg", detail="expected k=v")
            raise SystemExit(2)
        k, v = item.split("=", 1)
        arguments[k] = v
    try:
        result = ctx.client.tool_execute(name, arguments)
    except Exception as e:
        error("tool exec failed", detail=str(e))
        raise SystemExit(1)
    emit_json(result)
