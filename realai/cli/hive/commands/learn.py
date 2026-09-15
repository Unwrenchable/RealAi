"""Hive ``realai learn`` — static git-learn. Never starts heal / GPU / orch."""
from __future__ import annotations

import click

from realai.cli.hive.format import emit_json, error


@click.command("learn")
@click.argument("source", required=False, default=".")
@click.option("--write", is_flag=True, help="Scaffold or upgrade plugins/<slug>_coach/")
@click.option("--refresh", is_flag=True, help="Wipe disposable clone cache then reclone")
@click.pass_obj
def learn_cmd(ctx, source, write, refresh):
    """Scan a git source and write a learning packet (offline, no heal)."""
    try:
        from realai.learn.pipeline import run_learn

        data = run_learn(source or ".", write=bool(write), refresh=bool(refresh))
    except Exception as e:
        error("learn failed", detail=str(e))
        raise SystemExit(1)
    emit_json(data)
    if not data.get("ok"):
        raise SystemExit(1)
