#!/usr/bin/env python3
"""
RealAI Hive CLI — primary `realai` entry point.

Orchestrator-centric, agent-aware, GPU-honest. Craft is available via `realai craft`.
"""
from __future__ import annotations

import sys
from typing import List, Optional

import click

from realai.cli.hive.banner import collect_status, render_banner
from realai.cli.hive.commands.abilities import abilities_group, ability_group
from realai.cli.hive.commands.agents import agents_group
from realai.cli.hive.commands.chat import ask_cmd, chat_cmd
from realai.cli.hive.commands.craft_cmd import craft_cmd
from realai.cli.hive.commands.heal import heal_group
from realai.cli.hive.commands.learn import learn_cmd
from realai.cli.hive.commands.models import models_cmd, providers_cmd
from realai.cli.hive.commands.multi import multi_cmd
from realai.cli.hive.commands.quarantine import quarantine_group
from realai.cli.hive.commands.route import route_cmd, routes_cmd
from realai.cli.hive.commands.run import run_cmd
from realai.cli.hive.commands.stack import (
    gpu_group,
    orch_group,
    stack_group,
    vulkan_cmd,
)
from realai.cli.hive.commands.status import doctor_cmd, status_cmd, version_cmd
from realai.cli.hive.commands.tasks import task_group
from realai.cli.hive.commands.tools import tool_group, tools_group
from realai.cli.hive.commands.world import world_group
from realai.cli.hive.context import HiveContext, resolve_api_url
from realai.cli.hive.format import emit_json


@click.group(
    cls=click.Group,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option(
    "--api-url",
    envvar="REALAI_API_BASE",
    default=None,
    help="Orchestrator base URL (default http://127.0.0.1:8001)",
)
@click.option("--json", "as_json", is_flag=True, help="Machine-readable JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Verbose errors")
@click.option("--workspace", "-C", default=None, help="Workspace root")
@click.option("--home", default=None, help="Package/install home")
@click.pass_context
def cli(ctx, api_url, as_json, verbose, workspace, home):
    """
    RealAI Hive CLI — orchestrator-centric operator surface.

    \b
    Examples:
      realai
      realai status
      realai stack up
      realai route "refactor gpu resume"
      realai run "verify hive pipeline"
      realai agents --hive
      realai ability run chat_completion --input "ping"
      realai world show
      realai gpu status
    """
    obj = HiveContext(
        api_url=resolve_api_url(api_url),
        as_json=as_json,
        verbose=verbose,
        workspace=workspace,
        home=home,
    )
    obj.bind_workspace()
    ctx.obj = obj

    if ctx.invoked_subcommand is None:
        data = collect_status(obj)
        if as_json:
            emit_json(data)
        else:
            click.echo(render_banner(data))
            click.echo("Help:     realai --help")
            if not (data.get("orchestrator") or {}).get("ok"):
                click.echo("Next:     realai stack up")


# Core
cli.add_command(status_cmd)
cli.add_command(doctor_cmd)
cli.add_command(version_cmd)

# Stack / GPU
cli.add_command(stack_group)
cli.add_command(gpu_group)
cli.add_command(orch_group)
cli.add_command(vulkan_cmd)

# Models
cli.add_command(models_cmd)
cli.add_command(providers_cmd)

# Agent router + runners
cli.add_command(route_cmd)
cli.add_command(routes_cmd)
cli.add_command(run_cmd)
cli.add_command(agents_group)
cli.add_command(multi_cmd)
cli.add_command(task_group)

# Abilities / tools / heal / world / quarantine
cli.add_command(abilities_group)
cli.add_command(ability_group)
cli.add_command(tools_group)
cli.add_command(tool_group)
cli.add_command(heal_group)
cli.add_command(learn_cmd)
cli.add_command(world_group)
cli.add_command(quarantine_group)

# Chat (Hive) + Craft escape hatch
cli.add_command(chat_cmd)
cli.add_command(ask_cmd)
cli.add_command(craft_cmd)


def main(argv: Optional[List[str]] = None) -> int:
    try:
        cli.main(args=argv, prog_name="realai", standalone_mode=False)
        return 0
    except SystemExit as e:
        code = e.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        return 1
    except click.ClickException as e:
        e.show()
        return e.exit_code
    except Exception as e:
        click.echo(f"error: {e}", err=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
