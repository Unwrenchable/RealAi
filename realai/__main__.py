"""
python -m realai  /  realai

Portable craft CLI — full toolkit from *any* project folder.

  cd C:\\MyApp
  realai                      # chat in MyApp
  realai chat "fix tests"
  realai heal
  realai stack                # start GPU + orchestrator (+ UI)
  realai models / health / code / doctor / promote / ...
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional


def _bootstrap(argv: list[str]) -> tuple[list[str], argparse.Namespace]:
    """Parse global --workspace / --home before subcommands; bind env."""
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument(
        "--workspace",
        "-C",
        default=None,
        help="Workspace root (clamped to C:\\RealAI-clean inside product tree)",
    )
    pre.add_argument(
        "--home",
        default=None,
        help="Package/install dir (default: C:\\RealAI-clean\\realai)",
    )
    known, rest = pre.parse_known_args(argv)

    from realai.workspace import apply_workspace

    # Always bind; nested paths are clamped to the product workspace root.
    apply_workspace(known.workspace, home=known.home)
    return rest, known


def _home() -> Path:
    from realai.workspace import realai_home

    return realai_home()


def _ws() -> Path:
    from realai.workspace import realai_workspace

    return realai_workspace()


def _scripts() -> Path:
    from realai.workspace import workspace_scripts

    return workspace_scripts(_home())


def _run_ps1(script: Path, extra_args: Optional[list[str]] = None) -> int:
    if not script.is_file():
        print(f"missing script: {script}", file=sys.stderr)
        return 1
    shell = "pwsh" if _which("pwsh") else "powershell"
    cmd = [
        shell,
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        *(extra_args or []),
    ]
    print(f"[run] {' '.join(cmd)}")
    # Scripts and logs belong to the workspace root, not the package dir.
    return int(subprocess.call(cmd, cwd=str(_ws())))


def _which(name: str) -> Optional[str]:
    from shutil import which

    return which(name)


def _probe(url: str, timeout: float = 0.8) -> dict[str, Any]:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = body[:200]
            return {"ok": True, "status": r.status, "url": url, "body": data}
    except Exception as e:
        return {"ok": False, "url": url, "error": str(e)}


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _cmd_doctor(args: argparse.Namespace) -> int:
    from realai.doctor import run_doctor
    from realai.workspace import workspace_banner

    report = run_doctor(json_mode=bool(args.json))
    report["workspace_banner"] = workspace_banner()
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(workspace_banner())
        print(f"doctor ok={report.get('ok')}")
        for c in report.get("checks") or []:
            mark = "OK" if c.get("ok") else "FAIL"
            print(f"  [{mark}] {c.get('name')}: {c.get('detail')}")
    return 0 if report.get("ok") else 1


def _cmd_serve(args: argparse.Namespace) -> int:
    try:
        from realai.api_server import main as api_main

        return int(api_main() or 0)
    except TypeError:
        from realai.api_server import main as api_main

        api_main()
        return 0
    except Exception as e:
        print(f"serve failed: {e}", file=sys.stderr)
        print("Fallback: python api_server.py", file=sys.stderr)
        return 1


def _cmd_catalog(args: argparse.Namespace) -> int:
    from realai.ability_catalog import coverage_summary, learn_keywords_from_scans, save_catalog

    path = save_catalog()
    cov = coverage_summary()
    c = cov.get("coverage") or {}
    print(f"[catalog] wrote {path}")
    print(
        f"[catalog] coverage {c.get('weighted_pct')}% "
        f"live={c.get('live_count')} "
        f"external_roots {cov.get('external_roots_exist')}/{cov.get('external_roots_total')}"
    )
    if args.learn:
        learned = learn_keywords_from_scans()
        print(
            f"[catalog] learned keywords total={learned.get('total_count')} "
            f"added={learned.get('added_count')}"
        )
    if args.json:
        print(json.dumps(cov, indent=2, default=str))
    return 0


def _cmd_organs(args: argparse.Namespace) -> int:
    from modules.organs import hive_status

    st = hive_status()
    if args.json:
        print(json.dumps(st, indent=2, default=str))
    else:
        print(f"organs: {st.get('organ_count')} complete={st.get('complete')}")
        ids = st.get("ids") or []
        for i in ids[:20]:
            print(f"  - {i}")
        if len(ids) > 20:
            print(f"  ... +{len(ids) - 20} more")
    return 0


def _cmd_rackup(args: argparse.Namespace) -> int:
    from plugins.rackup_coach import METADATA, invoke

    if args.ability:
        payload = {}
        if args.payload_json:
            payload = json.loads(args.payload_json)
        res = invoke(
            {
                "ability": args.ability,
                "player": {"player_id": args.player_id or "cli"},
                "payload": payload,
                "organs_enabled": not args.no_organs,
            }
        )
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("ok") else 1

    print(f"rackup-coach v{METADATA.get('version')}")
    print(f"  ladder: {(METADATA.get('roc') or {}).get('ladder')}")
    print(f"  methods: {', '.join(METADATA.get('methods') or [])}")
    return 0


def _cmd_chat(args: argparse.Namespace) -> int:
    from realai.cli.craft import main as craft_main

    rest = list(getattr(args, "prompt", None) or [])
    if rest and rest[0] == "--":
        rest = rest[1:]
    return int(craft_main(rest) or 0)


def _cmd_code(args: argparse.Namespace) -> int:
    """Coding-focused one-shot or REPL with workspace bias."""
    from realai.cli.craft import CraftSession, ensure_gpu_server
    from realai.workspace import workspace_banner

    wait = int(os.environ.get("REALAI_GPU_WAIT") or "90")
    prompt_parts = list(getattr(args, "prompt", None) or [])
    if prompt_parts and prompt_parts[0] == "--":
        prompt_parts = prompt_parts[1:]
    task = " ".join(prompt_parts).strip()

    print(workspace_banner())
    st = ensure_gpu_server(wait_s=wait)
    print(f"[api] {st}")

    session = CraftSession()
    # prime with list so model sees project layout
    session.handle_stream("/list")
    if task:
        framed = (
            f"You are coding in workspace {_ws()}. "
            f"Task: {task}\n"
            "Inspect with tools if needed, then propose concrete file edits "
            "(full file content or clear patches). Prefer /write when sure."
        )
        session.handle_stream(framed)
        return 0

    print("Code mode — describe a task (or /quit). Workspace:", _ws())
    while True:
        try:
            user = input("\ncode> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return 0
        if not user:
            continue
        if user.lower() in ("/quit", "quit", "exit"):
            print("bye")
            return 0
        session.handle_stream(user)


def _cmd_heal(args: argparse.Namespace) -> int:
    from realai.cli.craft import tool_heal
    from realai.workspace import workspace_banner

    print(workspace_banner())
    r = tool_heal(force=bool(args.force))
    print(json.dumps(r, indent=2, default=str)[:4000])
    return 0 if r.get("ok") else 1


def _cmd_selfheal(args: argparse.Namespace) -> int:
    """
    Full self-heal pipeline.
      product tree → scripts/run_local_selfheal.ps1
      other projects → heal + optional one-shot craft improve prompt
    """
    from realai.workspace import is_realai_product_tree, workspace_banner

    print(workspace_banner())
    if is_realai_product_tree(_ws()) or getattr(args, "product", False):
        script = _scripts() / "run_local_selfheal.ps1"
        extra: list[str] = []
        if args.skip_start:
            extra.append("-SkipStart")
        if args.force:
            extra.append("-Force")
        if args.deepen:
            extra.extend(["-DeepenLoops", str(args.deepen)])
        return _run_ps1(script, extra)

    # project path
    from realai.cli.craft import CraftSession, ensure_gpu_server, tool_heal

    r = tool_heal(force=bool(args.force))
    print(json.dumps(r, indent=2, default=str)[:2500])
    if args.chat:
        ensure_gpu_server(wait_s=60)
        session = CraftSession()
        session.handle_stream(
            "Self-heal this project: review structure, git, and obvious issues; "
            "suggest concrete fixes. Workspace is the current project."
        )
    return 0 if r.get("ok") else 1


def _cmd_here(args: argparse.Namespace) -> int:
    from realai.cli.craft import tool_pwd

    print(json.dumps(tool_pwd(), indent=2, default=str))
    return 0


def _cmd_client(args: argparse.Namespace) -> int:
    from realai.cli.realai_cli import main as cli_main

    argv = list(args.cli_args or [])
    if argv and argv[0] == "--":
        argv = argv[1:]
    return int(cli_main(argv) or 0)


def _cmd_stack(args: argparse.Namespace) -> int:
    """Start Vulkan + orchestrator (+ voice env / console) from REALAI_HOME."""
    # Prefer unified Python launcher (Job-Object safe + voice/bot env).
    unified = _scripts() / "unified_stack.py"
    if unified.is_file() and not getattr(args, "skip_start", False):
        cmd = [sys.executable, str(unified)]
        if getattr(args, "stop", False):
            cmd.append("--stop")
        else:
            if getattr(args, "skip_ui", False):
                cmd.append("--no-console")
        return int(subprocess.call(cmd, cwd=str(_ws())))
    script = _scripts() / "run_local_chat.ps1"
    extra: list[str] = []
    if getattr(args, "stop", False):
        extra.append("-Stop")
    if args.skip_ui:
        extra.append("-SkipUI")
    if args.skip_start:
        extra.append("-SkipStart")
    if args.skip_promote:
        extra.append("-SkipPromote")
    return _run_ps1(script, extra)


def _cmd_server(args: argparse.Namespace) -> int:
    """Start Vulkan llama-server only (or ensure via craft)."""
    if args.via_craft:
        from realai.cli.craft import ensure_gpu_server

        st = ensure_gpu_server(wait_s=int(os.environ.get("REALAI_GPU_WAIT") or "90"))
        print(json.dumps(st, indent=2, default=str))
        return 0 if st.get("ok") else 1

    bat = _ws() / "start_realai_server.bat"
    if not bat.is_file():
        bat = _home() / "start_realai_server.bat"
    if bat.is_file():
        print(f"[run] {bat}")
        return int(subprocess.call(["cmd", "/c", str(bat)], cwd=str(_ws())))

    from realai.cli.craft import ensure_gpu_server

    st = ensure_gpu_server(wait_s=90)
    print(json.dumps(st, indent=2, default=str))
    return 0 if st.get("ok") else 1


def _cmd_orch(args: argparse.Namespace) -> int:
    """Start v3 orchestrator (expects Vulkan on :8080)."""
    host = args.host or "127.0.0.1"
    port = str(args.port or 8001)
    env = os.environ.copy()
    env["REALAI_VULKAN_BASE"] = env.get("REALAI_VULKAN_BASE") or "http://127.0.0.1:8080"
    env["REALAI_HOME"] = str(_home())
    env["REALAI_WORKSPACE"] = str(_ws())
    env["REALAI_PRODUCT_ROOT"] = str(_ws())
    env["PYTHONPATH"] = (
        str(_ws()) + os.pathsep + env.get("PYTHONPATH", "")
    )
    print(f"[orch] http://{host}:{port}  workspace={_ws()} home={_home()}")
    return int(
        subprocess.call(
            [
                sys.executable,
                "-m",
                "realai.v3_orchestrator",
                "--host",
                host,
                "--port",
                port,
            ],
            cwd=str(_ws()),
            env=env,
        )
    )


def _cmd_models(args: argparse.Namespace) -> int:
    from realai import model_catalog
    from realai.workspace import default_gguf, workspace_banner

    print(workspace_banner())
    print(f"default_gguf: {default_gguf()}")
    cat = model_catalog.build_catalog()
    data = cat.get("data") or []
    print(f"catalog models: {len(data)}  default={ (cat.get('realai') or {}).get('default_model') }")
    for m in data[:20]:
        r = m.get("realai") or {}
        print(f"  - {m.get('id')}  file={r.get('gguf_filename')}  loaded={r.get('loaded_now')}")
    if len(data) > 20:
        print(f"  ... +{len(data) - 20} more")
    if args.json:
        print(json.dumps(cat, indent=2, default=str)[:8000])
    return 0


def _cmd_setup(args: argparse.Namespace) -> int:
    script = _scripts() / "setup_local_llama.py"
    if not script.is_file():
        print("missing scripts/setup_local_llama.py", file=sys.stderr)
        return 1
    return int(subprocess.call([sys.executable, str(script)], cwd=str(_home())))


def _cmd_improve(args: argparse.Namespace) -> int:
    from realai.cli.craft import tool_improve

    r = tool_improve()
    print(json.dumps(r, indent=2, default=str)[:4000])
    return 0 if r.get("ok") else 1


def _cmd_promote(args: argparse.Namespace) -> int:
    script = _scripts() / "curated_promote.py"
    cmd = [sys.executable, str(script)]
    if args.dry_run:
        cmd.append("--dry-run")
    if args.force:
        cmd.append("--force")
    print(f"[promote] workspace={_ws()} home={_home()}")
    return int(subprocess.call(cmd, cwd=str(_ws())))


def _cmd_health(args: argparse.Namespace) -> int:
    from realai.workspace import workspace_banner

    print(workspace_banner())
    targets = [
        "http://127.0.0.1:8001/health",
        "http://127.0.0.1:8001/v1/models",
        "http://127.0.0.1:8080/health",
        "http://127.0.0.1:8080/v1/models",
        "http://127.0.0.1:8000/health",
        "http://127.0.0.1:3000",
    ]
    ok_any = False
    for u in targets:
        r = _probe(u)
        mark = "OK" if r.get("ok") else "--"
        detail = r.get("status") if r.get("ok") else r.get("error")
        print(f"  [{mark}] {u}  {detail}")
        ok_any = ok_any or bool(r.get("ok"))
    return 0 if ok_any else 1


def _cmd_gui(args: argparse.Namespace) -> int:
    gui = _ws() / "realai_gui.py"
    if not gui.is_file():
        gui = _home() / "realai_gui.py"
    if not gui.is_file():
        print("missing realai_gui.py", file=sys.stderr)
        return 1
    env = os.environ.copy()
    env["REALAI_HOME"] = str(_home())
    env["REALAI_WORKSPACE"] = str(_ws())
    env["REALAI_PRODUCT_ROOT"] = str(_ws())
    env["PYTHONPATH"] = (
        str(_ws()) + os.pathsep + env.get("PYTHONPATH", "")
    )
    print(f"[gui] workspace={_ws()} home={_home()}")
    return int(subprocess.call([sys.executable, str(gui)], cwd=str(_ws()), env=env))


def _cmd_local_server(args: argparse.Namespace) -> int:
    """Lightweight llama-cli OpenAI shim on :8000."""
    script = _ws() / "realai_local_server.py"
    if not script.is_file():
        script = _home() / "realai_local_server.py"
    if not script.is_file():
        print("missing realai_local_server.py", file=sys.stderr)
        return 1
    env = os.environ.copy()
    env["REALAI_HOME"] = str(_home())
    env["REALAI_WORKSPACE"] = str(_ws())
    env["REALAI_PRODUCT_ROOT"] = str(_ws())
    env["PYTHONPATH"] = (
        str(_ws()) + os.pathsep + env.get("PYTHONPATH", "")
    )
    return int(subprocess.call([sys.executable, str(script)], cwd=str(_ws()), env=env))


def _cmd_build(args: argparse.Namespace) -> int:
    """Local self-builder (no cloud API)."""
    from realai.self_builder import SelfBuilder

    task = " ".join(args.task or []).strip()
    if not task:
        print("usage: realai build \"task description\"", file=sys.stderr)
        return 2
    api = args.api_url or os.environ.get("REALAI_API_URL") or os.environ.get("REALAI_API_BASE")
    builder = SelfBuilder(
        api_url=api,
        model=args.model,
        max_steps=int(args.max_steps or 16),
        auto_confirm=not args.confirm,
    )
    result = builder.run(task)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") == "done" else 1


def _cmd_loop(args: argparse.Namespace) -> int:
    """Closed self-improvement loop (build + ingest + datasets)."""
    from realai.closed_loop import close_the_loop, check_server

    api = (
        args.api_url
        or os.environ.get("REALAI_API_URL")
        or os.environ.get("REALAI_API_BASE")
        or "http://127.0.0.1:8001"
    )
    if args.check_only:
        print(json.dumps(check_server(api), indent=2, default=str))
        return 0
    result = close_the_loop(
        api_url=api,
        task=args.task,
        model=args.model,
        max_steps=int(args.max_steps or 20),
        iterations=int(args.iterations or 1),
        skip_build=bool(args.ingest_only),
        auto_confirm=not args.confirm,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") in ("closed",) else 1


def _cmd_train(args: argparse.Namespace) -> int:
    """Native training pipeline stages."""
    from realai.training.pipeline import run_stage

    stage = args.stage or "status"
    out = run_stage(
        stage,
        model_id=args.model_id or "realai-1.0-instruct",
        data_dir=args.data_dir,
        max_steps=int(args.max_steps or 50),
        gguf=args.gguf,
        hf_dir=args.hf_dir,
    )
    print(json.dumps(out, indent=2, default=str))
    return 0 if out.get("status") not in ("error", "failed") else 1


def _cmd_tools(args: argparse.Namespace) -> int:
    """List global commands, ability tools, and bin shims."""
    from realai.workspace import workspace_banner

    print(workspace_banner())
    try:
        from realai.v3_runtime_bridge import tools_catalog, agent_tools_status

        cat = tools_catalog()
        print(f"In-tree tool catalog: {len(cat)} tools")
        for t in cat[:20]:
            print(f"  - {(t.get('function') or {}).get('name')}")
        if len(cat) > 20:
            print(f"  ... +{len(cat) - 20} more")
        print("agent_tools:", agent_tools_status())
    except Exception as e:
        print(f"tool catalog unavailable: {e}")
    print(
        """
Global commands (after install_global.ps1 — all work from any project):

  realai                 Interactive craft chat in cwd
  realai-chat            Same as realai chat
  realai-code            Coding-focused session
  realai-heal            Project heal / product promote
  realai-selfheal        Full self-heal pipeline
  realai-stack           Start Vulkan + orchestrator + UI
  realai-server          Vulkan llama-server only
  realai-orch            Orchestrator :8001
  realai-health          Probe :8001/:8080/:3000
  realai-models          List RealAI model ids + GGUFs
  realai-doctor          Install self-check
  realai-setup           Verify llama + models
  realai-improve         Ability catalog self-improve (HOME)
  realai-promote         Curated promote allowlist (product)
  realai-gui             Desktop GUI
  realai-local           Lightweight llama-cli API :8000
  realai tools           This help

Also: realai client | catalog | organs | rackup | serve | here

Env:
  REALAI_HOME        install tree (models)
  REALAI_WORKSPACE   project (default: cwd)
  realai -C PATH ... force workspace
""".strip()
    )
    bin_dir = _ws() / "bin"
    if not bin_dir.is_dir():
        bin_dir = _home() / "bin"
    if bin_dir.is_dir():
        print("\nbin shims:")
        for p in sorted(bin_dir.glob("*.cmd")):
            print(f"  {p.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="realai",
        description=(
            "RealAI portable toolkit. File tools use cwd (REALAI_WORKSPACE); "
            "models/stack come from REALAI_HOME."
        ),
    )
    p.add_argument("--workspace", "-C", default=None, help=argparse.SUPPRESS)
    p.add_argument("--home", default=None, help=argparse.SUPPRESS)

    sub = p.add_subparsers(dest="command")

    def add(name, help_, fn, **kwargs):
        sp = sub.add_parser(name, help=help_)
        for k, v in kwargs.items():
            # not used this way
            pass
        return sp

    chat = sub.add_parser("chat", help="Craft chat in current project (default)")
    chat.add_argument("prompt", nargs=argparse.REMAINDER)
    chat.set_defaults(func=_cmd_chat)

    craft = sub.add_parser("craft", help="Alias for chat")
    craft.add_argument("prompt", nargs=argparse.REMAINDER)
    craft.set_defaults(func=_cmd_chat)

    code = sub.add_parser("code", help="Coding session focused on current project")
    code.add_argument("prompt", nargs=argparse.REMAINDER)
    code.set_defaults(func=_cmd_code)

    d = sub.add_parser("doctor", help="Self-check RealAI install")
    d.add_argument("--json", action="store_true")
    d.set_defaults(func=_cmd_doctor)

    h = sub.add_parser("heal", help="Quick heal: product promote OR project diagnostics")
    h.add_argument("--force", action="store_true")
    h.set_defaults(func=_cmd_heal)

    sh = sub.add_parser("selfheal", help="Full self-heal pipeline (stack+promote or project)")
    sh.add_argument("--force", action="store_true")
    sh.add_argument("--skip-start", action="store_true")
    sh.add_argument("--deepen", type=int, default=0)
    sh.add_argument("--product", action="store_true", help="Force product selfheal scripts")
    sh.add_argument("--chat", action="store_true", help="After project heal, open craft advice")
    sh.set_defaults(func=_cmd_selfheal)

    here = sub.add_parser("here", help="Show REALAI_HOME + workspace")
    here.set_defaults(func=_cmd_here)
    pwd = sub.add_parser("pwd", help="Alias for here")
    pwd.set_defaults(func=_cmd_here)

    stack = sub.add_parser("stack", help="Start Vulkan + orchestrator + UI (from HOME)")
    stack.add_argument("--stop", action="store_true", help="Stop the chat stack instead")
    stack.add_argument("-Stop", dest="stop", action="store_true", help=argparse.SUPPRESS)
    stack.add_argument("--skip-ui", action="store_true")
    stack.add_argument("--skip-start", action="store_true")
    stack.add_argument("--skip-promote", action="store_true")
    stack.set_defaults(func=_cmd_stack)

    srv = sub.add_parser("server", help="Start Vulkan llama-server (:8080)")
    srv.add_argument("--via-craft", action="store_true", help="Use ensure_gpu_server helper")
    srv.set_defaults(func=_cmd_server)
    gpu = sub.add_parser("gpu", help="Alias for server")
    gpu.add_argument("--via-craft", action="store_true")
    gpu.set_defaults(func=_cmd_server)

    orch = sub.add_parser("orch", help="Start v3 orchestrator (:8001)")
    orch.add_argument("--host", default="127.0.0.1")
    orch.add_argument("--port", type=int, default=8001)
    orch.set_defaults(func=_cmd_orch)

    health = sub.add_parser("health", help="Probe local RealAI endpoints")
    health.set_defaults(func=_cmd_health)

    models = sub.add_parser("models", help="List RealAI model catalog + GGUFs")
    models.add_argument("--json", action="store_true")
    models.set_defaults(func=_cmd_models)

    setup = sub.add_parser("setup", help="Verify llama-server + local models")
    setup.set_defaults(func=_cmd_setup)

    improve = sub.add_parser("improve", help="Ability catalog self-improve (HOME)")
    improve.set_defaults(func=_cmd_improve)

    promote = sub.add_parser("promote", help="Curated promote allowlist (product)")
    promote.add_argument("--dry-run", action="store_true")
    promote.add_argument("--force", action="store_true")
    promote.set_defaults(func=_cmd_promote)

    gui = sub.add_parser("gui", help="Launch desktop GUI")
    gui.set_defaults(func=_cmd_gui)

    local = sub.add_parser("local", help="Lightweight llama-cli API on :8000")
    local.set_defaults(func=_cmd_local_server)

    tools = sub.add_parser("tools", help="List global toolkit commands")
    tools.set_defaults(func=_cmd_tools)

    build = sub.add_parser("build", help="Self-builder: improve workspace with local model + repo tools")
    build.add_argument("task", nargs=argparse.REMAINDER)
    build.add_argument("--api-url", default=None)
    build.add_argument("--model", default=None)
    build.add_argument("--max-steps", type=int, default=16)
    build.add_argument("--confirm", action="store_true", help="Require confirm for edits/commands")
    build.set_defaults(func=_cmd_build)

    loop = sub.add_parser("loop", help="Closed self-improve loop (build + train ingest)")
    loop.add_argument("--api-url", default=None)
    loop.add_argument("--task", default=None)
    loop.add_argument("--model", default=None)
    loop.add_argument("--max-steps", type=int, default=20)
    loop.add_argument("--iterations", type=int, default=1)
    loop.add_argument("--check-only", action="store_true")
    loop.add_argument("--ingest-only", action="store_true")
    loop.add_argument("--confirm", action="store_true")
    loop.set_defaults(func=_cmd_loop)

    train = sub.add_parser("train", help="Native training pipeline (datasets/plan/finetune/export/status)")
    train.add_argument("--stage", default="status", help="datasets|plan|finetune|export|status|eval|all")
    train.add_argument("--model-id", default="realai-1.0-instruct")
    train.add_argument("--data-dir", default=None)
    train.add_argument("--max-steps", type=int, default=50)
    train.add_argument("--gguf", default=None)
    train.add_argument("--hf-dir", default=None)
    train.set_defaults(func=_cmd_train)

    s = sub.add_parser("serve", help="Start legacy OpenAI-compatible API server")
    s.set_defaults(func=_cmd_serve)

    c = sub.add_parser("catalog", help="Build ability catalog + optional keyword learn")
    c.add_argument("--learn", action="store_true")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=_cmd_catalog)

    o = sub.add_parser("organs", help="Show synthetic organs hive status")
    o.add_argument("--json", action="store_true")
    o.set_defaults(func=_cmd_organs)

    r = sub.add_parser("rackup", help="RackUp coach metadata or invoke ability")
    r.add_argument("--ability", default="")
    r.add_argument("--player-id", default="cli")
    r.add_argument("--payload-json", default="")
    r.add_argument("--no-organs", action="store_true")
    r.set_defaults(func=_cmd_rackup)

    cl = sub.add_parser("client", help="HTTP client CLI against a running server")
    cl.add_argument("cli_args", nargs=argparse.REMAINDER)
    cl.set_defaults(func=_cmd_client)

    return p


KNOWN_CMDS = {
    "chat",
    "craft",
    "code",
    "doctor",
    "heal",
    "selfheal",
    "here",
    "pwd",
    "stack",
    "server",
    "gpu",
    "orch",
    "health",
    "models",
    "setup",
    "improve",
    "promote",
    "gui",
    "local",
    "tools",
    "build",
    "loop",
    "train",
    "serve",
    "catalog",
    "organs",
    "rackup",
    "client",
    "-h",
    "--help",
}


def _hive_argv(rest: list[str]) -> bool:
    """Hive CLI verbs the product argparse does not accept (stack up, status, agents)."""
    if not rest:
        return False
    cmd = rest[0]
    sub = rest[1] if len(rest) > 1 else ""
    if cmd in {
        "status",
        "agents",
        "route",
        "routes",
        "run",
        "multi",
        "ability",
        "abilities",
        "world",
        "quarantine",
        "version",
        "task",
        "tasks",
        "vulkan",
        "providers",
        "ask",
    }:
        return True
    if cmd == "stack" and sub in ("up", "down", "status"):
        return True
    if cmd == "gpu" and sub in ("status", "resume", "stop", "start"):
        return True
    if cmd == "orch" and sub in ("status", "start"):
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    rest, _pre = _bootstrap(raw)

    if not rest or rest[0] in ("-h", "--help"):
        if rest and rest[0] in ("-h", "--help"):
            build_parser().print_help()
            print("\nDefault with no args: interactive craft chat in current directory")
            print("List toolkit:  realai tools")
            print("Install global:  powershell -File C:\\RealAI-clean\\scripts\\install_global.ps1")
            return 0
        from realai.cli.craft import main as craft_main

        return int(craft_main([]) or 0)

    if _hive_argv(rest):
        from realai.cli.hive.app import main as hive_main

        return int(hive_main(rest) or 0)

    if rest[0] not in KNOWN_CMDS:
        from realai.cli.craft import main as craft_main

        return int(craft_main(rest) or 0)

    parser = build_parser()
    args = parser.parse_args(rest)
    if not getattr(args, "command", None):
        from realai.cli.craft import main as craft_main

        return int(craft_main([]) or 0)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
