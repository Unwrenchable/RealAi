"""Ability: bridge to the installed realai-cli (C:\\tools\\realai, Node) - read-only / paper only.

realai-cli (trading engines, DexScreener/Jupiter market data, rug-watch, paper
trading, local UI) is not vendored into this repo: its tree carries runtime
state, wallet helpers and operator config. This bridge shells to the installed
CLI instead and only allows read-only and paper commands.

Resolution: ``REALAI_CLI_BIN`` (path to realai.cmd / realai.js) ->
``C:\\tools\\realai\\realai.js`` -> ``realai-cli`` on PATH.
Blocked: any ``--live``/``--yes``/``--broadcast`` flag and the commands that can
move funds (trade, trading, wallet, solana send, web3, dex swap, do, update).
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from typing import Any

ABILITY = {
    "id": "realai_cli_bridge",
    "name": "realai_cli_bridge",
    "type": "ability",
    "status": "PARTIAL",
    "source": "C:\\tools\\realai (realai-cli 1.1.0, Node) via subprocess",
    "dest": "abilities/realai_cli_bridge.py",
    "capabilities": ["market_read", "token_scan", "rug_watch", "paper_trading", "backtest", "portfolio_read"],
    "secrets_policy": "never passes keys; live/send commands blocked",
}

READ_ONLY_COMMANDS = {
    "status", "health", "help", "capabilities", "abilities", "models", "market", "scan", "token",
    "portfolio", "paper", "backtest", "risk", "strategy", "alerts", "watch", "research", "explain",
    "recall", "find", "system", "brain",
}
BLOCKED_FLAGS = {"--live", "--yes", "-y", "--broadcast", "--send", "--execute"}
BLOCKED_WORDS = {"send", "swap", "buy", "sell", "transfer", "withdraw", "approve", "sign", "launch"}


def resolve_cli() -> list[str] | None:
    env = (os.getenv("REALAI_CLI_BIN") or "").strip()
    cands = [env] if env else []
    cands += [r"C:\tools\realai\realai.js", os.path.expanduser("~/tools/realai/realai.js")]
    for c in cands:
        if c and os.path.isfile(c):
            if c.endswith(".js"):
                node = shutil.which("node")
                return [node, c] if node else None
            return [c]
    found = shutil.which("realai-cli")
    return [found] if found else None


def check_args(args: list[str]) -> str | None:
    if not args:
        return "command required"
    cmd = args[0].lower()
    if cmd not in READ_ONLY_COMMANDS:
        return f"command not allowed through the bridge: {cmd}"
    low = [a.lower() for a in args]
    if any(a in BLOCKED_FLAGS or a.startswith("--live") for a in low):
        return "live/confirm flags are blocked"
    if cmd != "paper" and any(a in BLOCKED_WORDS for a in low[1:]):
        return "value-moving subcommand blocked"
    return None


def run(input: str = "", context: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    args = ctx.get("args")
    if not isinstance(args, list):
        args = shlex.split(str(ctx.get("command") or input or "status"))
    args = [str(a) for a in args]
    err = check_args(args)
    if err:
        return {"ok": False, "ability": "realai_cli_bridge", "status": "blocked", "error": err, "args": args}
    cli = resolve_cli()
    if not cli:
        return {"ok": False, "ability": "realai_cli_bridge", "status": "unavailable",
                "error": "realai-cli not found (set REALAI_CLI_BIN or install C:\\tools\\realai)"}
    env = {k: v for k, v in os.environ.items() if not k.upper().endswith(("PRIVATE_KEY", "SECRET", "MNEMONIC"))}
    env["REALAI_NO_LIVE"] = "1"
    try:
        p = subprocess.run(cli + args, capture_output=True, text=True, timeout=int(ctx.get("timeout") or 120), env=env)
    except Exception as exc:
        return {"ok": False, "ability": "realai_cli_bridge", "status": "error", "error": f"{type(exc).__name__}: {exc}"}
    return {"ok": p.returncode == 0, "ability": "realai_cli_bridge", "status": "success" if p.returncode == 0 else "error",
            "args": args, "exit_code": p.returncode, "stdout": p.stdout[-8000:], "stderr": p.stderr[-2000:], "real": True}
