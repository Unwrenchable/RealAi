"""In-tree RealAI CLI surface (bin/*.cmd + craft) — not the hollow C:\\tools\\realai husk."""

from __future__ import annotations

from pathlib import Path
from typing import Any

ABILITY = {
    "id": "cli_surface",
    "name": "cli_surface",
    "type": "ability",
    "status": "LIVE",
    "source": "bin/realai*.cmd + realai.cli.craft",
    "dest": "abilities/cli_surface.py",
    "capabilities": ["cli", "doctor", "craft", "dispatch"],
    "secrets_policy": "none",
}

_ROOT = Path(__file__).resolve().parents[1]


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or input or "status").lower().strip()

    bin_dir = _ROOT / "bin"
    cmds = sorted(p.name for p in bin_dir.glob("realai*.cmd")) if bin_dir.is_dir() else []
    craft = _ROOT / "realai" / "cli" / "craft.py"
    root_cmd = _ROOT / "realai.cmd"

    if action in {"doctor", "health"}:
        from realai.cli.craft import tool_doctor

        return {
            "ok": True,
            "ability": "cli_surface",
            "action": "doctor",
            "doctor": tool_doctor(),
            "commands": cmds,
        }

    husk = Path(r"C:\tools\realai")
    husk_note = "hollow husk — not used; see scan_results/TOOLS_CLI_FOLD.md"
    husk_exists = husk.is_dir()

    return {
        "ok": True,
        "ability": "cli_surface",
        "action": "status",
        "home": str(_ROOT),
        "entrypoint": str(root_cmd) if root_cmd.is_file() else None,
        "craft": str(craft) if craft.is_file() else None,
        "bin_commands": cmds,
        "command_count": len(cmds),
        "usage": [
            "realai",
            "realai doctor",
            "realai chat \"...\"",
            "bin\\realai-stack.cmd",
            "bin\\realai-orch.cmd",
        ],
        "tools_cli_husk": {"path": str(husk), "exists": husk_exists, "note": husk_note},
    }
