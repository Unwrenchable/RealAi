"""
Cross-league rating intelligence: APA, BCA, TAP, VNEA ↔ shared RackUp ladder.

Source: RACKUP_GAME_KNOWLEDGE_AND_AI_CONTRACT.md §C
Estimates for matchmaking/display — not official handicaps.
"""
from __future__ import annotations

from typing import Any, Optional


RACKUP_MIN, RACKUP_MAX = 100, 3000
DEFAULT_SEED = 500

SYSTEMS = ("apa", "bca", "tap", "vnea", "rackup", "fargo")


def clamp_rackup(x: float) -> int:
    return int(max(RACKUP_MIN, min(RACKUP_MAX, round(x))))


def band_from_rackup(rating: float) -> str:
    r = float(rating or 0)
    if r < 500:
        return "novice_new"
    if r < 900:
        return "novice"
    if r < 1500:
        return "intermediate"
    if r < 2100:
        return "advanced"
    return "pro"


def apa_to_rackup(sl: float) -> int:
    """APA skill level 1–9 → RackUp center estimate."""
    try:
        sl_f = float(sl)
    except (TypeError, ValueError):
        return DEFAULT_SEED
    # table centers + smooth formula
    table = {2: 700, 3: 950, 4: 1200, 5: 1500, 6: 1850, 7: 2200, 8: 2500, 9: 2700}
    if int(round(sl_f)) in table:
        return table[int(round(sl_f))]
    return clamp_rackup(400 + sl_f * 250)


def rackup_to_apa(rating: float) -> float:
    r = float(rating or 500)
    # invert roughly
    sl = (r - 400) / 250.0
    return max(1.0, min(9.0, round(sl * 2) / 2))  # half steps ok


def bca_to_rackup(value: float, scale: str = "auto") -> int:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return DEFAULT_SEED
    sc = (scale or "auto").lower()
    if sc in ("skill_1_9", "skill", "sl"):
        return apa_to_rackup(v)
    if sc == "raw_x10":
        return clamp_rackup(v * 10)
    if sc == "continuum":
        return clamp_rackup(v)
    # auto
    if v <= 9.5:
        return apa_to_rackup(v)
    if v <= 100:
        return clamp_rackup(v * 22)
    return clamp_rackup(v)


def tap_to_rackup(value: float, scale: str = "auto") -> int:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return DEFAULT_SEED
    sc = (scale or "auto").lower()
    if sc in ("skill_1_9", "skill", "sl") or (sc == "auto" and v <= 9.5):
        return apa_to_rackup(v)
    if sc == "points_20_100" or (sc == "auto" and 20 <= v <= 100):
        return clamp_rackup(300 + v * 20)
    if sc == "fargo_like" or (sc == "auto" and 200 <= v <= 800):
        return clamp_rackup(v)
    return clamp_rackup(300 + v * 15)


def vnea_to_rackup(value: Any, scale: str = "auto") -> int:
    if isinstance(value, str):
        t = value.strip().upper()
        tier = {
            "D": 800,
            "C": 1100,
            "B": 1500,
            "A": 1900,
            "OPEN": 2300,
            "TOP": 2400,
        }
        if t in tier:
            return tier[t]
        # "DIVISION B" etc.
        for k, rv in tier.items():
            if k in t:
                return rv
    try:
        v = float(value)
    except (TypeError, ValueError):
        return DEFAULT_SEED
    if v <= 9.5:
        return apa_to_rackup(v)
    return clamp_rackup(v)


def to_rackup(
    system: str,
    value: Any,
    scale: str = "auto",
) -> dict[str, Any]:
    sys = (system or "rackup").strip().lower()
    if sys in ("rackup", "shared"):
        try:
            r = clamp_rackup(float(value))
        except (TypeError, ValueError):
            r = DEFAULT_SEED
        conf = 0.95
    elif sys == "apa":
        r = apa_to_rackup(value)
        conf = 0.75
    elif sys == "bca":
        r = bca_to_rackup(value, scale=scale)
        conf = 0.65 if scale == "auto" else 0.75
    elif sys == "tap":
        r = tap_to_rackup(value, scale=scale)
        conf = 0.6
    elif sys == "vnea":
        r = vnea_to_rackup(value, scale=scale)
        conf = 0.6
    elif sys == "fargo":
        r = clamp_rackup(float(value) if value is not None else DEFAULT_SEED)
        conf = 0.7
    else:
        r = DEFAULT_SEED
        conf = 0.3
    return {
        "rackup_rating_estimate": r,
        "band": band_from_rackup(r),
        "confidence": conf,
        "from_system": sys,
        "from_value": value,
        "from_scale": scale,
    }


def equivalents_from_rackup(rating: float) -> dict[str, Any]:
    r = float(rating or DEFAULT_SEED)
    apa = rackup_to_apa(r)
    # VNEA tier from rating
    if r < 950:
        vnea = "D"
    elif r < 1300:
        vnea = "C"
    elif r < 1700:
        vnea = "B"
    elif r < 2100:
        vnea = "A"
    else:
        vnea = "OPEN"
    bca_skill = apa
    bca_cont = clamp_rackup(r / 22) if r > 100 else r  # reverse rough ×22
    return {
        "apa": {"value": apa, "display": f"SL {apa}"},
        "bca": {
            "value": bca_skill,
            "display": f"skill ~{bca_skill}",
            "alt_continuum": min(100, max(1, int(r / 22))),
        },
        "tap": {"value": apa, "display": f"skill ~{apa}"},
        "vnea": {"value": vnea, "display": f"Division {vnea}" if len(vnea) == 1 else vnea},
        "rackup": {"value": clamp_rackup(r), "display": f"RackUp {clamp_rackup(r)}"},
    }


def convert_rating(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Ability rating_convert implementation.
    """
    payload = payload or {}
    from_system = str(payload.get("from_system") or payload.get("system") or "apa")
    from_value = payload.get("from_value", payload.get("value"))
    from_scale = str(payload.get("from_scale") or payload.get("scale") or "auto")

    primary = to_rackup(from_system, from_value, from_scale)
    rackup = primary["rackup_rating_estimate"]
    conf = primary["confidence"]

    # Blend also_known if present
    also = list(payload.get("also_known") or [])
    estimates = [rackup]
    for item in also:
        if not isinstance(item, dict):
            continue
        est = to_rackup(
            str(item.get("system") or ""),
            item.get("value"),
            str(item.get("scale") or "auto"),
        )
        estimates.append(est["rackup_rating_estimate"])
        conf = min(conf, est["confidence"] + 0.05)
    if len(estimates) > 1:
        rackup = clamp_rackup(sum(estimates) / len(estimates))
        conf = min(0.85, conf + 0.05)

    return {
        "rackup_rating_estimate": rackup,
        "band": band_from_rackup(rackup),
        "confidence": round(conf, 2),
        "equivalents": equivalents_from_rackup(rackup),
        "method": "table_v1",
        "notes": "Estimate only; not official handicap. Shared RackUp ladder is competitive truth after match history.",
        "input": {
            "from_system": from_system,
            "from_value": from_value,
            "from_scale": from_scale,
            "also_known_count": len(also),
        },
    }


def resolve_effective_rating(
    player: Any,
    *,
    prefer_rackup_after_matches: int = 5,
) -> dict[str, Any]:
    """
    Choose competitive rating for matchmaking / updates.
    Preference: primary_rating_system → most trusted recent league → APA→BCA→TAP→VNEA
    → RackUp shared if matches_played enough.
    """
    # Player may be PlayerProfile or dict
    if hasattr(player, "to_dict"):
        d = player.to_dict()
    elif isinstance(player, dict):
        d = player
    else:
        d = {}

    rackup = d.get("rating")
    try:
        rackup_f = float(rackup) if rackup is not None else None
    except (TypeError, ValueError):
        rackup_f = None

    matches = int(d.get("matches_played_rackup") or d.get("matches_played") or 0)
    league = d.get("league_ratings") or {}
    meta = d.get("league_ratings_meta") or {}
    primary = (d.get("primary_rating_system") or "").strip().lower()

    if matches >= prefer_rackup_after_matches and rackup_f is not None:
        return {
            "rating": clamp_rackup(rackup_f),
            "source": "rackup_shared",
            "confidence": 0.9,
            "equivalents": equivalents_from_rackup(rackup_f),
        }

    candidates: list[tuple[float, str, Any, str]] = []  # priority, system, value, scale
    # lower priority number = better
    order = {"apa": 1, "bca": 2, "tap": 3, "vnea": 4}

    if primary and league.get(primary) is not None:
        scale = (meta.get(primary) or {}).get("scale") or "auto"
        est = to_rackup(primary, league.get(primary), scale)
        return {
            "rating": est["rackup_rating_estimate"],
            "source": f"primary:{primary}",
            "confidence": est["confidence"],
            "equivalents": equivalents_from_rackup(est["rackup_rating_estimate"]),
        }

    # trusted + recency
    best = None
    best_key = (99, "")
    for sys, val in (league.items() if isinstance(league, dict) else []):
        if val is None:
            continue
        m = meta.get(sys) or {}
        trusted = 0 if m.get("trusted") else 1
        pri = order.get(str(sys).lower(), 50)
        key = (trusted, pri)
        if key < best_key:
            best_key = key
            scale = m.get("scale") or "auto"
            best = to_rackup(str(sys), val, scale)
            best["source"] = f"league:{sys}"

    if best:
        return {
            "rating": best["rackup_rating_estimate"],
            "source": best.get("source"),
            "confidence": best["confidence"],
            "equivalents": equivalents_from_rackup(best["rackup_rating_estimate"]),
        }

    if rackup_f is not None:
        return {
            "rating": clamp_rackup(rackup_f),
            "source": "rackup_shared",
            "confidence": 0.8,
            "equivalents": equivalents_from_rackup(rackup_f),
        }

    return {
        "rating": DEFAULT_SEED,
        "source": "default_seed",
        "confidence": 0.2,
        "equivalents": equivalents_from_rackup(DEFAULT_SEED),
    }
