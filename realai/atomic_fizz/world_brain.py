"""World-brain / omnibrain prompt + fallback encounter logic.

Ported from Atomic Fizz ``scripts/realai/world-brain.js`` + ``omnibrain.js``
(engines_gold). No Node required for Hive tools.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

ENCOUNTER_TYPES = {
    "npc",
    "dungeon",
    "event",
    "merchant",
    "faction_patrol",
    "hazard",
    "discovery",
    "none",
}

# Lightweight region → faction map (subset of systems/region-influence.js)
_REGIONS: Dict[str, Dict[str, Any]] = {
    "mojave outskirts": {"palette": "dust brown", "factions": ["NCR", "Scavengers"], "vibe": "dry, tense"},
    "vault 77": {"palette": "sterile blue", "factions": ["Vault Dwellers"], "vibe": "claustrophobic"},
    "ruined vegas strip": {"palette": "neon ruins", "factions": ["Raiders", "Merchants"], "vibe": "chaotic"},
    "vault": {"palette": "sterile blue", "factions": ["Vault Dwellers", "merchant"], "vibe": "claustrophobic"},
    "settlement": {"palette": "dust brown", "factions": ["NCR", "merchant", "caravan"], "vibe": "tense"},
    "ruin": {"palette": "neon ruins", "factions": ["Raiders"], "vibe": "chaotic"},
    "unknown": {"palette": "dust brown", "factions": ["Wanderers"], "vibe": "neutral"},
}


def _obj(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def build_region_influence(region: str) -> Dict[str, Any]:
    key = str(region or "unknown").strip()
    low = key.lower() or "unknown"
    if low in _REGIONS:
        out = dict(_REGIONS[low])
        out["region"] = key or "unknown"
        return out
    for name, meta in _REGIONS.items():
        if name in low or low in name:
            out = dict(meta)
            out["region"] = key
            return out
    out = dict(_REGIONS["unknown"])
    out["region"] = key or "unknown"
    return out


def build_world_brain_system_prompt() -> str:
    return """
ATOMICFIZZCAPS - REALAI OMNIBRAIN MASTER PROMPT
(Unified AR Encounter Engine + World Simulator + NPC/Quest/Event/Dungeon Generator)

SYSTEM ROLE - REALAI OMNIBRAIN
You are RealAI, the unified world-brain of the Atomic Fizz Caps Wasteland Geo-Game.

You control and generate:
- AR encounters, NPCs, Quests, Dialogue, World events, Dungeon entrances
- Faction patrols, Hazards, Discoveries, Region-specific content
- Cell-tuned difficulty, Player-shaped world evolution, Weather / raider / caravan sim

You ALWAYS output clean JSON for structured content and short, punchy lines for dialogue.
You NEVER break schema. You ALWAYS stay in Fallout-style tone: gritty, dusty, punchy, atmospheric.
""".strip()


def build_world_brain_context(seed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = _obj(seed)
    region = data.get("region")
    if not isinstance(region, (str, dict)):
        region = "unknown"
    return {
        "player": _obj(data.get("player")),
        "region": region,
        "cell": _obj(data.get("cell")),
        "world_state": _obj(data.get("world_state") or data.get("worldState") or data.get("worldstate")),
        "faction_influence": _obj(data.get("faction_influence") or data.get("factionInfluence")),
        "ar_context": _obj(data.get("ar_context") or data.get("arContext")),
        "time_of_day": data.get("time_of_day") or data.get("timeOfDay") or "unknown",
        "difficulty_tuning": data.get("difficulty_tuning") or data.get("difficultyTuning") or "balanced",
        "engagement_tuning": data.get("engagement_tuning") or data.get("engagementTuning") or "neutral",
    }


def build_world_brain_context_block(seed: Optional[Dict[str, Any]] = None) -> str:
    return "WORLD BRAIN CONTEXT:\n" + json.dumps(build_world_brain_context(seed), indent=2)


def build_omnibrain_master_prompt(
    seed: Optional[Dict[str, Any]] = None,
    region_rules: Optional[Dict[str, Any]] = None,
) -> str:
    ctx = build_world_brain_context(seed)
    rules = region_rules or build_region_influence(str(ctx.get("region") or "unknown"))
    return (
        f"{build_world_brain_system_prompt()}\n\n"
        f"REGION RULES:\n{json.dumps(rules, indent=2)}\n\n"
        f"{build_world_brain_context_block(seed)}\n\n"
        "Decide the next encounter. Reply JSON only with keys: "
        "encounter_type (npc|dungeon|event|merchant|faction_patrol|hazard|discovery|none), "
        "reason (short string), seed (object)."
    )


def _chance_bucket(inp: Dict[str, Any]) -> int:
    player = _obj(inp.get("player"))
    cell = _obj(inp.get("cell"))
    raw = json.dumps(
        {
            "player": player.get("id") or "unknown",
            "region": inp.get("region") or "unknown",
            "cell": cell.get("id") or "cell",
            "last_encounter_time": player.get("last_encounter_time") or 0,
        },
        sort_keys=True,
    )
    h = 0
    for ch in raw:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h % 100


def _build_tuning(inp: Dict[str, Any]) -> Dict[str, Any]:
    cell = _obj(inp.get("cell"))
    worldstate = _obj(inp.get("worldstate") or inp.get("world_state"))
    feedback = cell.get("feedback_tags") if isinstance(cell.get("feedback_tags"), list) else []
    inventory = _obj(inp.get("player")).get("inventory")
    inventory = inventory if isinstance(inventory, list) else []
    danger = -1 if cell.get("danger_feedback") == "too_hard" else 1 if cell.get("danger_feedback") == "too_easy" else 0
    reward = 1 if cell.get("engagement") == "low" or "fun" in feedback else 0
    interest = cell.get("engagement") == "low" or "boring" in feedback
    if worldstate.get("weather") == "rad_storm":
        danger = max(-2, danger - 1)
    if not inventory or "boring" in feedback:
        reward = 1
    return {
        "danger_adjustment": danger,
        "reward_adjustment": min(1, reward),
        "interest_boost": bool(interest),
    }


def _fallback_seed(inp: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "player": _obj(inp.get("player")),
        "region": str(inp.get("region") or "unknown")[:64],
        "cell": _obj(inp.get("cell")),
        "worldstate": _obj(inp.get("worldstate") or inp.get("world_state")),
        "ar_mode": bool(inp.get("ar_mode")),
        "tuning": _build_tuning(inp),
    }


def _opposed(player_alignment: Any, factions: List[str]) -> bool:
    if not player_alignment or not factions:
        return False
    alignment = str(player_alignment).lower()
    joined = " ".join(factions).lower()
    if alignment == "evil" and re.search(r"ncr|vault|merchant|caravan", joined):
        return True
    if alignment == "good" and "raider" in joined:
        return True
    return False


def fallback_encounter_decision(inp: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Deterministic omnibrain fallback (no LLM) — mirrors omnibrain.js pickFallbackEncounter."""
    inp = dict(inp or {})
    cell = _obj(inp.get("cell"))
    worldstate = _obj(inp.get("worldstate") or inp.get("world_state"))
    cooldowns = _obj(inp.get("cooldowns"))
    feedback = cell.get("feedback_tags") if isinstance(cell.get("feedback_tags"), list) else []
    player = _obj(inp.get("player"))
    ar_mode = bool(inp.get("ar_mode"))
    region_rules = build_region_influence(str(inp.get("region") or "unknown"))
    region_factions = list(region_rules.get("factions") or [])
    encounter_cd = float(cooldowns.get("encounter") or 0)
    dungeon_cd = float(cooldowns.get("dungeon") or 0)
    merchant_cd = float(cooldowns.get("merchant") or 0)
    chance = _chance_bucket(inp)
    weather = worldstate.get("weather") or "clear"
    raider = worldstate.get("raider_activity") or "low"
    caravans = worldstate.get("caravans") if isinstance(worldstate.get("caravans"), list) else []
    inventory = player.get("inventory") if isinstance(player.get("inventory"), list) else []

    if encounter_cd > 0:
        return {"encounter_type": "none", "reason": "cooldown or low probability", "seed": {}}
    if weather in {"dust_storm", "rad_storm"}:
        return {"encounter_type": "hazard", "reason": "severe weather pushes a hazard encounter", "seed": _fallback_seed(inp)}
    if (
        dungeon_cd <= 0
        and ar_mode
        and "unsafe" not in feedback
        and cell.get("engagement") == "high"
        and cell.get("danger_feedback") == "balanced"
    ):
        return {"encounter_type": "dungeon", "reason": "safe high-engagement cell favors a dungeon entrance", "seed": _fallback_seed(inp)}
    if merchant_cd <= 0 and caravans and not inventory:
        return {"encounter_type": "merchant", "reason": "nearby caravans and low supplies favor a merchant encounter", "seed": _fallback_seed(inp)}
    if region_factions and _opposed(player.get("alignment"), region_factions):
        return {"encounter_type": "faction_patrol", "reason": "faction influence clashes with player alignment", "seed": _fallback_seed(inp)}
    if (weather == "night_chill" or raider == "high") and cell.get("traffic") == "high":
        return {"encounter_type": "event", "reason": "worldstate pressure spikes a world event", "seed": _fallback_seed(inp)}
    if cell.get("danger_feedback") == "too_easy":
        return {"encounter_type": "hazard", "reason": "easy cell gets a hazard spike", "seed": _fallback_seed(inp)}
    if ar_mode and (cell.get("engagement") == "low" or "boring" in feedback):
        return {"encounter_type": "discovery", "reason": "low engagement cell gets a discovery boost", "seed": _fallback_seed(inp)}
    if ar_mode and cell.get("traffic") in {"high", "medium"} and cell.get("engagement") == "low" and region_factions:
        return {"encounter_type": "npc", "reason": "ar mode and faction presence favor an npc encounter", "seed": _fallback_seed(inp)}
    if chance < 25 and cell.get("danger_feedback") == "balanced" and cell.get("engagement") != "low":
        return {"encounter_type": "none", "reason": "cooldown or low probability", "seed": {}}
    return {
        "encounter_type": "npc" if ar_mode else "event",
        "reason": "ar mode favors a readable npc encounter" if ar_mode else "default fallback event",
        "seed": _fallback_seed(inp),
    }
