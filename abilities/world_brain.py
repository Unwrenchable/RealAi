"""World-brain ability — prompt/context builders for Atomic Fizz wasteland sim."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "world_brain",
    "name": "world_brain",
    "type": "ability",
    "status": "LIVE",
    "source": "realai.atomic_fizz.world_brain + engines_gold/world-brain.js",
    "dest": "abilities/world_brain.py",
    "capabilities": ["world_brain", "omnibrain_prompt", "region_influence"],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    from realai.atomic_fizz import world_brain as wb

    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or input or "prompt").lower().strip()
    seed = ctx.get("seed") if isinstance(ctx.get("seed"), dict) else {
        k: ctx[k]
        for k in ("player", "region", "cell", "world_state", "worldstate", "ar_mode", "cooldowns")
        if k in ctx
    }
    if ctx.get("region") and "region" not in seed:
        seed["region"] = ctx.get("region")
    # Prefer explicit region; otherwise use free-text input when it isn't an action verb
    if not seed.get("region"):
        if input and input.strip().lower() not in {"prompt", "context", "region", "influence", "ctx"}:
            seed["region"] = input.strip()

    region = str(seed.get("region") or ctx.get("region") or "unknown")
    rules = wb.build_region_influence(region)

    if action in {"region", "influence"}:
        return {"ok": True, "ability": "world_brain", "action": "region", "region": rules}

    if action in {"context", "ctx"}:
        return {
            "ok": True,
            "ability": "world_brain",
            "action": "context",
            "context": wb.build_world_brain_context(seed),
            "block": wb.build_world_brain_context_block(seed),
        }

    # default: full omnibrain master prompt
    return {
        "ok": True,
        "ability": "world_brain",
        "action": "prompt",
        "region": rules,
        "system_prompt": wb.build_world_brain_system_prompt(),
        "prompt": wb.build_omnibrain_master_prompt(seed, rules),
        "source": "engines_gold/world-brain.js",
    }
