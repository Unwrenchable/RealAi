"""Git-learn ability — static scan / packet / optional coach stub. Never heal."""
from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "learn_git",
    "name": "learn_git",
    "type": "ability",
    "status": "LIVE",
    "source": "realai/learn_git.py",
    "dest": "abilities/learn_git.py",
    "capabilities": [
        "learn_git",
        "git_learn",
        "catalog",
        "plugins",
    ],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    source = str(
        ctx.get("source") or ctx.get("path") or ctx.get("url") or (input or "").strip() or "."
    )
    write = bool(ctx.get("write") or ctx.get("--write"))
    refresh = bool(ctx.get("refresh"))
    all_branches = ctx.get("all_branches")
    if all_branches is None:
        all_branches = True
    max_branches = ctx.get("max_branches")
    max_files = ctx.get("max_files")
    from realai.learn.pipeline import run_learn
    from realai.learn.scan import DEFAULT_MAX_BRANCHES, FINGERPRINT_CAP

    return run_learn(
        source,
        write=write,
        refresh=refresh,
        all_branches=bool(all_branches),
        max_branches=int(max_branches or DEFAULT_MAX_BRANCHES),
        max_files=int(max_files or FINGERPRINT_CAP),
    )
