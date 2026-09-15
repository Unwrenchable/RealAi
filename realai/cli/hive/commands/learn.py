"""Hive ``realai learn`` — static git-learn. Never starts heal / GPU / orch."""
from __future__ import annotations

import click

from realai.cli.hive.format import emit_json, error
from realai.learn.scan import DEFAULT_MAX_BRANCHES, FINGERPRINT_CAP


@click.command("learn")
@click.argument("source", required=False, default=".")
@click.option("--write", is_flag=True, help="Scaffold or upgrade plugins/<slug>_coach/")
@click.option("--refresh", is_flag=True, help="Wipe disposable clone cache then reclone")
@click.option(
    "--all-branches/--no-all-branches",
    default=True,
    show_default=True,
    help="Scan every git branch (Travis default: on)",
)
@click.option(
    "--max-branches",
    type=int,
    default=DEFAULT_MAX_BRANCHES,
    show_default=True,
    help="Cap branches scanned",
)
@click.option(
    "--max-files",
    type=int,
    default=FINGERPRINT_CAP,
    show_default=True,
    help="Cap unique file fingerprints",
)
@click.pass_obj
def learn_cmd(ctx, source, write, refresh, all_branches, max_branches, max_files):
    """Scan a git source (all branches) and write a learning packet (offline, no heal)."""
    try:
        from realai.learn.pipeline import run_learn

        data = run_learn(
            source or ".",
            write=bool(write),
            refresh=bool(refresh),
            all_branches=bool(all_branches),
            max_branches=int(max_branches),
            max_files=int(max_files),
        )
    except Exception as e:
        error("learn failed", detail=str(e))
        raise SystemExit(1)
    emit_json(data)
    if not data.get("ok"):
        raise SystemExit(1)
