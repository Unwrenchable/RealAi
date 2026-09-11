"""status / doctor / version commands."""
from __future__ import annotations

import click

from realai.cli.hive.banner import collect_status, render_banner
from realai.cli.hive.format import emit_json, kv, section


@click.command("status")
@click.option("--json", "as_json", is_flag=True, help="JSON output")
@click.pass_obj
def status_cmd(ctx, as_json):
    """Show Hive orchestrator + Vulkan + agent status."""
    if as_json:
        ctx.as_json = True
    data = collect_status(ctx)
    if ctx.as_json:
        emit_json(data)
        return
    click.echo(render_banner(data))
    orch = data.get("orchestrator") or {}
    vul = data.get("vulkan") or {}
    click.echo(section("Endpoints"))
    click.echo(kv("api", data.get("api_url")))
    click.echo(kv("orch", f"{'up' if orch.get('ok') else 'down'}  {orch.get('status') or orch.get('error') or ''}"))
    click.echo(kv("vulkan", f"{'up' if vul.get('ok') else 'down'}  {vul.get('base') or ''}"))
    if not orch.get("ok"):
        click.echo("\nNext:  realai stack up")


@click.command("doctor")
@click.option("--json", "as_json", is_flag=True, help="JSON output")
@click.pass_obj
def doctor_cmd(ctx, as_json):
    """Self-check install paths and hive surfaces."""
    from pathlib import Path
    import os

    if as_json:
        ctx.as_json = True
    checks = []
    data = collect_status(ctx)
    checks.append(("orchestrator", bool((data.get("orchestrator") or {}).get("ok"))))
    checks.append(("vulkan", bool((data.get("vulkan") or {}).get("ok"))))
    hive = data.get("hive") or {}
    checks.append(("hive_mode", bool(hive.get("hive_mode"))))

    vulkan_dir = Path(os.environ.get("REALAI_VULKAN_DIR") or r"C:\llama-vulkan")
    models_dir = Path(os.environ.get("REALAI_MODELS_DIR") or r"C:\models\checkpoints_lora")
    checks.append(("llama-server.exe", (vulkan_dir / "llama-server.exe").is_file()))
    checks.append(("llama-cli.exe", (vulkan_dir / "llama-cli.exe").is_file()))
    checks.append(("checkpoints_lora", models_dir.is_dir()))
    checks.append(("agents/hive", (Path(data.get("workspace") or ".") / "agents" / "hive").is_dir()))
    checks.append((".github/agents", (Path(data.get("workspace") or ".") / ".github" / "agents").is_dir()))

    payload = {"checks": {k: v for k, v in checks}, "status": data}
    if ctx.as_json:
        emit_json(payload)
        return
    click.echo(render_banner(data))
    click.echo(section("Doctor"))
    for name, ok in checks:
        click.echo(f"  [{'OK' if ok else '!!'}] {name}")
    failed = [n for n, ok in checks if not ok]
    if failed:
        click.echo(f"\nfailed: {', '.join(failed)}")
        raise SystemExit(1)


@click.command("version")
def version_cmd():
    """Print Hive CLI version."""
    click.echo("RealAI Hive CLI 1.0.0")
