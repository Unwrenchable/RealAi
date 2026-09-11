"""Omnibrain ability — encounter decisions (fallback + optional Hive LLM)."""

from __future__ import annotations

import json
import urllib.request
from typing import Any

ABILITY = {
    "id": "omnibrain",
    "name": "omnibrain",
    "type": "ability",
    "status": "LIVE",
    "source": "realai.atomic_fizz.world_brain + engines_gold/omnibrain.js",
    "dest": "abilities/omnibrain.py",
    "capabilities": ["omnibrain", "encounter_decision", "wasteland_sim"],
    "secrets_policy": "none — no wallet keys",
}


def _hive_chat_json(prompt: str, system: str) -> dict[str, Any] | None:
    try:
        body = json.dumps(
            {
                "model": "realai-default-coder",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 400,
                "temperature": 0.4,
            }
        ).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:8001/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        try:
            return json.loads(content)
        except Exception:
            import re

            m = re.search(r"\{[\s\S]*\}", content)
            if m:
                return json.loads(m.group(0))
    except Exception:
        return None
    return None


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    from realai.atomic_fizz import world_brain as wb

    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or "decide").lower().strip()
    seed = ctx.get("seed") if isinstance(ctx.get("seed"), dict) else {}
    # flatten common fields onto seed
    for k in ("player", "region", "cell", "worldstate", "world_state", "ar_mode", "cooldowns"):
        if k in ctx and k not in seed:
            seed[k] = ctx[k]
    if input and "region" not in seed:
        # allow "decide Mojave Outskirts" style
        if action in {"decide", "fallback", "prompt"} and not seed:
            seed["region"] = input
        elif action == "decide":
            seed.setdefault("region", input)

    if action in {"prompt", "build_prompt"}:
        rules = wb.build_region_influence(str(seed.get("region") or "unknown"))
        return {
            "ok": True,
            "ability": "omnibrain",
            "action": "prompt",
            "prompt": wb.build_omnibrain_master_prompt(seed, rules),
            "region": rules,
        }

    if action in {"fallback", "heuristic"}:
        decision = wb.fallback_encounter_decision(seed)
        return {
            "ok": True,
            "ability": "omnibrain",
            "action": "fallback",
            "decision": decision,
            "mode": "heuristic",
            "source": "engines_gold/omnibrain.js pickFallbackEncounter",
        }

    # decide: try LLM then fallback
    use_llm = bool(ctx.get("llm", True))
    decision = None
    mode = "heuristic"
    if use_llm:
        rules = wb.build_region_influence(str(seed.get("region") or "unknown"))
        prompt = wb.build_omnibrain_master_prompt(seed, rules)
        parsed = _hive_chat_json(prompt, wb.build_world_brain_system_prompt())
        if isinstance(parsed, dict) and parsed.get("encounter_type") in wb.ENCOUNTER_TYPES:
            decision = {
                "encounter_type": parsed.get("encounter_type"),
                "reason": str(parsed.get("reason") or "llm")[:120],
                "seed": parsed.get("seed") if isinstance(parsed.get("seed"), dict) else wb.fallback_encounter_decision(seed).get("seed"),
            }
            mode = "hive_llm"

    if decision is None:
        decision = wb.fallback_encounter_decision(seed)
        mode = "heuristic"

    return {
        "ok": True,
        "ability": "omnibrain",
        "action": "decide",
        "decision": decision,
        "mode": mode,
        "input_region": seed.get("region"),
        "source": "engines_gold/omnibrain.js",
    }
