"""Escape hatch to Craft REPL (secondary surface)."""
from __future__ import annotations

import click


@click.command(
    "craft",
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.pass_context
def craft_cmd(ctx):
    """Launch Craft (compat). Prefer Hive commands for agent/orchestrator work."""
    from realai.cli import craft as craft_mod

    argv = list(ctx.args)
    raise SystemExit(craft_mod.main(argv))
