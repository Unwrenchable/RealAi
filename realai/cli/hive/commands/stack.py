"""stack / gpu / orch / vulkan commands."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import click

from realai.cli.hive.format import emit_json, error, ok_line


def _scripts_dir(ctx) -> Path:
    ws = Path(getattr(ctx, "workspace", None) or os.environ.get("REALAI_HOME") or r"C:\RealAI-clean")
    return ws / "scripts"


def _load_vulkan_runtime(ctx):
    scripts = _scripts_dir(ctx)
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import vulkan_runtime  # type: ignore

    return vulkan_runtime


def _orch_up(api_url: str, timeout: float = 2.0) -> bool:
    import urllib.request

    try:
        with urllib.request.urlopen(api_url.rstrip("/") + "/health", timeout=timeout):
            return True
    except Exception:
        return False


def _start_orch(ctx) -> dict:
    if _orch_up(ctx.api_url):
        return {"ok": True, "status": "already_running", "url": ctx.api_url}
    root = Path(getattr(ctx, "workspace", None) or r"C:\RealAI-clean")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    env.setdefault("ORCH_PORT", "8001")
    env.setdefault("REALAI_API_BASE", ctx.api_url)
    env.setdefault("REALAI_VULKAN_BASE", "http://127.0.0.1:8080")
    env.setdefault("REALAI_SELF_IMPROVE", "1")
    log_dir = root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    out = open(log_dir / "v3-orchestrator.out.log", "a", encoding="utf-8")
    err = open(log_dir / "v3-orchestrator.err.log", "a", encoding="utf-8")
    if os.name == "nt":
        # Start-Process escapes Job Objects that reap Popen children on starter exit.
        out.close()
        err.close()
        log_out = log_dir / "v3-orchestrator.out.log"
        log_err = log_dir / "v3-orchestrator.err.log"
        py = sys.executable.replace("'", "''")
        cwd = str(root).replace("'", "''")
        # Pass critical env vars inline for the new process.
        env.setdefault("REALAI_BOT_VOICE", "1")
        env.setdefault("REALAI_BOT_TOOLS", "1")
        env.setdefault("REALAI_BOT_LOCAL_ONLY", "1")
        env.setdefault("REALAI_MODELS_DIR", r"C:\models\checkpoints_lora")
        env.setdefault("REALAI_TTS_BACKEND", "kokoro")
        env_assigns = "; ".join(
            "$env:{k}='{v}'".format(k=k, v=str(v).replace("'", "''"))
            for k, v in env.items()
            if k
            in {
                "PYTHONPATH",
                "REALAI_HOME",
                "REALAI_ROOT",
                "REALAI_WORKSPACE",
                "REALAI_PRODUCT_ROOT",
                "REALAI_VULKAN_BASE",
                "REALAI_API_BASE",
                "REALAI_SELF_IMPROVE",
                "REALAI_BOT_VOICE",
                "REALAI_BOT_TOOLS",
                "REALAI_BOT_LOCAL_ONLY",
                "REALAI_MODELS_DIR",
                "REALAI_GGUF",
                "REALAI_TTS_BACKEND",
                "REALAI_KOKORO_MODEL_DIR",
                "REALAI_FISH_MODEL_DIR",
                "REALAI_XTTS_MODEL_DIR",
                "ORCH_PORT",
            }
            and v
        )
        ps = (
            "{env}; Start-Process -FilePath '{py}' "
            "-ArgumentList @('-m','realai.v3_orchestrator') "
            "-WorkingDirectory '{cwd}' -WindowStyle Hidden "
            "-RedirectStandardOutput '{out}' -RedirectStandardError '{err}'"
        ).format(
            env=env_assigns or "$null=$null",
            py=py,
            cwd=cwd,
            out=str(log_out).replace("'", "''"),
            err=str(log_err).replace("'", "''"),
        )
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                ps,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    else:
        flags = 0
        if hasattr(subprocess, "DETACHED_PROCESS"):
            flags |= subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
        if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
            flags |= subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
        subprocess.Popen(
            [sys.executable, "-m", "realai.v3_orchestrator"],
            cwd=str(root),
            env=env,
            stdout=out,
            stderr=err,
            creationflags=flags or 0,
            start_new_session=True,
            close_fds=True,
        )
    for _ in range(25):
        time.sleep(1)
        if _orch_up(ctx.api_url):
            return {"ok": True, "status": "started", "url": ctx.api_url}
    return {"ok": False, "status": "timeout", "url": ctx.api_url}


@click.group("stack")
def stack_group():
    """Start/stop the Hive stack (Vulkan + orchestrator)."""


@stack_group.command("up")
@click.option("--force", is_flag=True, help="Restart even if already up")
@click.option("--no-console", is_flag=True, help="Do not open console.html")
@click.pass_obj
def stack_up(ctx, force, no_console):
    """Bring up Vulkan + orchestrator (+ voice env / console speak-aloud)."""
    # Prefer unified launcher (Job-Object safe + full voice/bot env).
    try:
        scripts = _scripts_dir(ctx)
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        import unified_stack  # type: ignore

        payload = unified_stack.stack_up(force=bool(force), open_console=not bool(no_console))
        if ctx.as_json:
            emit_json(payload)
        else:
            vul = payload.get("vulkan") or {}
            orch = payload.get("orchestrator") or {}
            click.echo(f"vulkan: {vul.get('status')} model={vul.get('model')}")
            click.echo(f"orch:    {orch.get('status')} {orch.get('url')}")
            click.echo(
                "voice:   REALAI_BOT_VOICE={0} (orch WAV / Windows SAPI + browser fallback)".format(
                    (payload.get("env") or {}).get("REALAI_BOT_VOICE")
                )
            )
            status = payload.get("status") or {}
            if status.get("console"):
                click.echo(f"console: {status.get('console')}")
            if payload.get("ok"):
                ok_line("stack up")
            else:
                error("stack incomplete", hint="python scripts/unified_stack.py --status")
                raise SystemExit(1)
        return
    except SystemExit:
        raise
    except Exception as e:
        click.echo(f"[stack] unified launcher fallback: {e}", err=True)
    vr = _load_vulkan_runtime(ctx)
    vul = vr.resume_vulkan(wait_s=120.0)
    orch = _start_orch(ctx)
    payload = {"vulkan": vul, "orchestrator": orch, "ok": bool(vul.get("ok") and orch.get("ok"))}
    if ctx.as_json:
        emit_json(payload)
    else:
        click.echo(f"vulkan: {vul.get('status')} model={vul.get('model')}")
        click.echo(f"orch:    {orch.get('status')} {orch.get('url')}")
        if payload["ok"]:
            ok_line("stack up")
        else:
            error("stack incomplete", hint="realai doctor")
            raise SystemExit(1)


@stack_group.command("down")
@click.pass_obj
def stack_down(ctx):
    """Stop Vulkan llama-server (frees VRAM). Orchestrator left running unless --all."""
    vr = _load_vulkan_runtime(ctx)
    stopped = vr.pause_vulkan()
    if ctx.as_json:
        emit_json({"stopped": stopped})
    else:
        ok_line(f"paused vulkan: {stopped or 'none'}")


@stack_group.command("status")
@click.pass_obj
def stack_status(ctx):
    """Show stack component health."""
    from realai.cli.hive.banner import collect_status, render_banner

    data = collect_status(ctx)
    if ctx.as_json:
        emit_json({"orchestrator": data.get("orchestrator"), "vulkan": data.get("vulkan")})
    else:
        click.echo(render_banner(data))


@click.group("gpu")
def gpu_group():
    """Vulkan GPU backend (C:\\llama-vulkan + checkpoints_lora)."""


@gpu_group.command("status")
@click.pass_obj
def gpu_status(ctx):
    from pathlib import Path

    from realai.cli.hive.gpu_inspector import inspect as gpu_inspect

    ws = Path(getattr(ctx, "workspace", None) or r"C:\RealAI-clean")
    payload = gpu_inspect(ws)
    if ctx.as_json:
        emit_json(payload)
        return
    paths = payload.get("paths") or {}
    click.echo(f"server  {paths.get('server_exe')}  exists={paths.get('server_exists')}")
    click.echo(f"cli     {paths.get('cli_exe')}  exists={paths.get('cli_exists')}")
    click.echo(f"models  {paths.get('models_dir')}")
    click.echo(f"gguf    {paths.get('default_resume_gguf')}")
    click.echo(f"health  {payload.get('health')}")
    if payload.get("note"):
        click.echo(f"note    {payload['note']}")


@gpu_group.command("resume")
@click.option("--gguf", default="", help="Override GGUF path/filename")
@click.option("--force", is_flag=True, help="Restart even if already up")
@click.pass_obj
def gpu_resume(ctx, gguf, force):
    """Resume llama-server after train VRAM pause."""
    vr = _load_vulkan_runtime(ctx)
    result = vr.resume_vulkan(gguf or None, force_restart=force, wait_s=120.0)
    if ctx.as_json:
        emit_json(result)
    else:
        click.echo(result)
    if not result.get("ok"):
        raise SystemExit(1)


@gpu_group.command("stop")
@click.pass_obj
def gpu_stop(ctx):
    """Kill llama-server to free AMD VRAM."""
    vr = _load_vulkan_runtime(ctx)
    stopped = vr.pause_vulkan()
    if ctx.as_json:
        emit_json({"stopped": stopped})
    else:
        ok_line(f"stopped: {stopped or 'none'}")


@gpu_group.command("start")
@click.option("--gguf", default="", help="Override GGUF path/filename")
@click.pass_obj
def gpu_start(ctx, gguf):
    """Alias for gpu resume."""
    vr = _load_vulkan_runtime(ctx)
    result = vr.resume_vulkan(gguf or None, wait_s=120.0)
    if ctx.as_json:
        emit_json(result)
    else:
        click.echo(result)
    if not result.get("ok"):
        raise SystemExit(1)


@click.group("orch")
def orch_group():
    """v3 orchestrator (:8001)."""


@orch_group.command("status")
@click.pass_obj
def orch_status(ctx):
    up = _orch_up(ctx.api_url)
    payload = {"ok": up, "url": ctx.api_url}
    if up:
        try:
            payload["health"] = ctx.client.health()
        except Exception as e:
            payload["error"] = str(e)
    if ctx.as_json:
        emit_json(payload)
    else:
        click.echo(f"orch {'up' if up else 'down'}  {ctx.api_url}")


@orch_group.command("start")
@click.pass_obj
def orch_start(ctx):
    result = _start_orch(ctx)
    if ctx.as_json:
        emit_json(result)
    else:
        click.echo(result)
    if not result.get("ok"):
        raise SystemExit(1)


@click.command("vulkan")
@click.pass_obj
def vulkan_cmd(ctx):
    """Inspect Vulkan binaries and model paths."""
    vr = _load_vulkan_runtime(ctx)
    payload = {"paths": vr.paths(), "port_up": vr.port_up(), "health": vr.health()}
    if ctx.as_json:
        emit_json(payload)
    else:
        click.echo(f"server  {payload['paths'].get('server_exe')}  exists={payload['paths'].get('server_exists')}")
        click.echo(f"cli     {payload['paths'].get('cli_exe')}  exists={payload['paths'].get('cli_exists')}")
        click.echo(f"models  {payload['paths'].get('models_dir')}")
        click.echo(f"health  {payload['health']}")
