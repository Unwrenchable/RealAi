"""
Cross-league rating intelligence → shared continuous ROC / RackUp ladder.

Source of truth: ROC_SYSTEM_DESIGN.md §7
  - Continuous BCA/Fargo-like number (not APA SL as competitive core)
  - Display bands: Novice / Intermediate / Advanced / Expert / Elite (labels only)
  - Canonical chip: `{Band} • {exact_rating}` e.g. Advanced • 547
  - Convert APA / BCA / Fargo / TAP / VNEA with confidence
  - Preference: primary → trusted recent → Fargo/BCA → APA → TAP → VNEA
  - After matches_played_rackup ≥ 5, shared ladder is competitive truth

Estimates for onboarding/matchmaking — not official handicaps.
RealAI computes; RackUp persists users.rating only.
"""
from __future__ import annotations

from typing import Any, Optional

from plugins.rackup_coach.roc import DEFAULT_ROC_SEED, ROC_RATING_MAX, ROC_RATING_MIN

RACKUP_MIN, RACKUP_MAX = ROC_RATING_MIN, ROC_RATING_MAX
DEFAULT_SEED = DEFAULT_ROC_SEED

SYSTEMS = ("apa", "bca", "fargo", "tap", "vnea", "rackup", "roc")

# APA SL → continuous ROC centers (§7.2.3)
APA_TO_ROC = {
    1: 280,
    2: 320,
    3: 420,
    4: 520,
    5: 600,
    6: 680,
    7: 760,
    8: 820,
    9: 880,
}

# VNEA tier centers (§7.2.3 illustrative)
VNEA_TO_ROC = {
    "D": 400,
    "C": 480,
    "B": 540,
    "A": 640,
    "OPEN": 740,
    "TOP": 780,
    "LOWER": 415,
    "MID": 540,
    "UPPER": 660,
}


def clamp_rackup(x: float) -> int:
    return int(max(RACKUP_MIN, min(RACKUP_MAX, round(x))))


def display_band(rating: float | int | None) -> str:
    """
    ROC locked display bands (§7.1.2) — labels only.
    Must not drive matchmaking, handicaps, or rating_update inputs.
    """
    r = float(rating or 0)
    if r < 400:
        return "Novice"
    if r < 500:
        return "Intermediate"
    if r < 600:
        return "Advanced"
    if r < 700:
        return "Expert"
    return "Elite"


def format_rating_chip(rating: float | int | None) -> str:
    """Canonical UI chip: Advanced • 547"""
    r = clamp_rackup(float(rating or DEFAULT_SEED))
    return f"{display_band(r)} • {r}"


def band_from_rackup(rating: float) -> str:
    """
    Lowercase slug for internal APIs.
    Prefer display_band() for ROC UI; this remains for backward compat.
    """
    return display_band(rating).lower()


def coach_band_from_rating(rating: float) -> str:
    """
    Curriculum band for coach/SOTD content selection on ROC continuous scale.
    Separate from display bands (5-level UI chips).
    """
    r = float(rating or 0)
    if r < 400:
        return "beginner"
    if r < 550:
        return "intermediate"
    if r < 700:
        return "advanced"
    return "pro"


def apa_to_rackup(sl: float) -> int:
    """APA skill level 1–9 → ROC continuous center estimate."""
    try:
        sl_f = float(sl)
    except (TypeError, ValueError):
        return DEFAULT_SEED
    key = int(round(sl_f))
    if key in APA_TO_ROC:
        # smooth half-steps between centers
        if abs(sl_f - key) < 0.01:
            return APA_TO_ROC[key]
        lo = int(sl_f)
        hi = lo + 1
        if lo in APA_TO_ROC and hi in APA_TO_ROC:
            frac = sl_f - lo
            return clamp_rackup(
                APA_TO_ROC[lo] + frac * (APA_TO_ROC[hi] - APA_TO_ROC[lo])
            )
        return APA_TO_ROC[key]
    # linear SL2→320 … SL7→760
    return clamp_rackup(320 + (sl_f - 2.0) * ((760 - 320) / 5.0))


def rackup_to_apa(rating: float) -> float:
    r = float(rating or DEFAULT_SEED)
    # nearest center
    best_sl, best_d = 4.0, 1e9
    for sl, center in APA_TO_ROC.items():
        d = abs(center - r)
        if d < best_d:
            best_d = d
            best_sl = float(sl)
    return best_sl


def bca_to_rackup(value: float, scale: str = "auto") -> int:
    """
    BCA / continuum → ROC.
    Fargo-like ~200–800: prefer pass-through.
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return DEFAULT_SEED
    sc = (scale or "auto").lower()
    if sc in ("skill_1_9", "skill", "sl"):
        return apa_to_rackup(v)
    if sc in ("fargo", "fargo_rate", "continuum", "raw"):
        return clamp_rackup(v)
    if sc == "raw_x10":
        return clamp_rackup(v * 10 if v <= 100 else v)
    # auto
    if v <= 9.5:
        return apa_to_rackup(v)
    # Fargo / BCA continuum family — pass-through
    if 150 <= v <= 900:
        return clamp_rackup(v)
    if v <= 100:
        # alternate 0–100 scale → stretch toward ROC mid
        return clamp_rackup(200 + v * 5.5)
    return clamp_rackup(v)


def fargo_to_rackup(value: float, scale: str = "fargo") -> int:
    return bca_to_rackup(value, scale=scale or "fargo")


def tap_to_rackup(value: float, scale: str = "auto") -> int:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return DEFAULT_SEED
    sc = (scale or "auto").lower()
    if sc in ("skill_1_9", "skill", "sl") or (sc == "auto" and v <= 9.5):
        return apa_to_rackup(v)
    if sc in ("points_20_100", "charter") or (sc == "auto" and 20 <= v <= 100):
        # mid-pack ~500; map 20→320, 100→780
        return clamp_rackup(320 + (v - 20) * ((780 - 320) / 80.0))
    if sc in ("fargo_like", "fargo") or (sc == "auto" and 200 <= v <= 800):
        return clamp_rackup(v)
    return clamp_rackup(320 + v * 40)  # low confidence path


def vnea_to_rackup(value: Any, scale: str = "auto") -> int:
    if isinstance(value, str):
        t = value.strip().upper()
        if t in VNEA_TO_ROC:
            return VNEA_TO_ROC[t]
        for k, rv in VNEA_TO_ROC.items():
            if k in t:
                return rv
        # "mid division" style
        if "MID" in t or "MIDDLE" in t:
            return VNEA_TO_ROC["MID"]
        if "LOW" in t:
            return VNEA_TO_ROC["LOWER"]
        if "UPP" in t or "HIGH" in t:
            return VNEA_TO_ROC["UPPER"]
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
    if sys in ("rackup", "shared", "roc"):
        try:
            r = clamp_rackup(float(value))
        except (TypeError, ValueError):
            r = DEFAULT_SEED
        conf = 0.95
    elif sys == "apa":
        r = apa_to_rackup(value)
        conf = 0.68
    elif sys in ("bca", "fargo", "fargorate", "fargo_rate"):
        r = bca_to_rackup(value, scale=scale)
        conf = 0.82 if scale in ("fargo", "continuum", "raw") or (
            isinstance(value, (int, float)) and 150 <= float(value) <= 900
        ) else 0.7
        if sys.startswith("fargo"):
            conf = max(conf, 0.8)
    elif sys == "tap":
        r = tap_to_rackup(value, scale=scale)
        conf = 0.55 if scale == "auto" else 0.65
    elif sys == "vnea":
        r = vnea_to_rackup(value, scale=scale)
        conf = 0.55
    else:
        r = DEFAULT_SEED
        conf = 0.3
    return {
        "rackup_rating_estimate": r,
        "band": band_from_rackup(r),
        "band_label": display_band(r),
        "display": format_rating_chip(r),
        "confidence": conf,
        "from_system": sys,
        "from_value": value,
        "from_scale": scale,
    }


def equivalents_from_rackup(rating: float) -> dict[str, Any]:
    r = float(rating or DEFAULT_SEED)
    apa = rackup_to_apa(r)
    if r < 450:
        vnea = "D"
    elif r < 510:
        vnea = "C"
    elif r < 600:
        vnea = "B"
    elif r < 700:
        vnea = "A"
    else:
        vnea = "OPEN"
    return {
        "apa": {"value": apa, "display": f"SL {apa}"},
        "bca": {
            "value": clamp_rackup(r),
            "display": f"~{clamp_rackup(r)} continuum",
            "alt_skill": apa,
        },
        "fargo": {
            "value": clamp_rackup(r),
            "display": f"~{clamp_rackup(r)}",
        },
        "tap": {"value": apa, "display": f"skill ~{apa}"},
        "vnea": {
            "value": vnea,
            "display": f"Division {vnea}" if len(str(vnea)) <= 4 else str(vnea),
        },
        "rackup": {
            "value": clamp_rackup(r),
            "display": format_rating_chip(r),
        },
        "roc": {
            "value": clamp_rackup(r),
            "display": format_rating_chip(r),
            "band_label": display_band(r),
        },
    }


def convert_rating(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Ability rating_convert — estimate continuous ROC rating, then Glicko-2 seed.

    Cross-league → seed_from_external (high RD from low confidence).
    Glicko-2 takes over after rated ROC matches.
    """
    payload = payload or {}
    from_system = str(payload.get("from_system") or payload.get("system") or "apa")
    from_value = payload.get("from_value", payload.get("value"))
    from_scale = str(payload.get("from_scale") or payload.get("scale") or "auto")

    primary = to_rackup(from_system, from_value, from_scale)
    rackup = primary["rackup_rating_estimate"]
    conf = primary["confidence"]

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

    from plugins.rackup_coach.glicko2 import seed_from_external

    seed = seed_from_external(
        rackup,
        confidence=conf,
        player_id=str(payload.get("player_id") or ""),
        from_system=from_system,
        from_value=from_value,
    )

    return {
        "rackup_rating_estimate": rackup,
        "band": band_from_rackup(rackup),
        "band_label": display_band(rackup),
        "display": format_rating_chip(rackup),
        "confidence": round(conf, 2),
        "equivalents": equivalents_from_rackup(rackup),
        "method": "table_v1_roc_glicko2_seed",
        "ladder": "roc_glicko2",
        "glicko2_seed": seed,
        "rd": seed["rd"],
        "volatility": seed["volatility"],
        "seed": seed.get("seed"),
        "notes": (
            "Estimate converted to ROC Glicko-2 seed (elevated RD when confidence low). "
            "Bands are labels only — matchmaking uses exact rating + RD uncertainty. "
            "Not an official APA/BCA/TAP/VNEA handicap. Glicko-2 takes over after play."
        ),
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
    Choose competitive continuous rating for matchmaking / updates.
    Preference (§7.2.2):
      1. primary_rating_system if set
      2. most recent trusted:true
      3. FargoRate/BCA continuous → APA SL → TAP → VNEA
      4. Once matches_played_rackup ≥ 5, shared ladder only
    """
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

    from plugins.rackup_coach.glicko2 import DEFAULT_RD, DEFAULT_VOL, seed_from_external

    host_rd = d.get("rd", d.get("rating_deviation"))
    host_vol = d.get("volatility", d.get("vol", d.get("sigma")))

    def _with_glicko(
        rating: float,
        *,
        source: str,
        confidence: float,
        rd: float | None = None,
        volatility: float | None = None,
        seed: bool = False,
    ) -> dict[str, Any]:
        out: dict[str, Any] = {
            "rating": clamp_rackup(rating),
            "source": source,
            "confidence": confidence,
            "band_label": display_band(rating),
            "display": format_rating_chip(rating),
            "equivalents": equivalents_from_rackup(rating),
            "ladder": "roc_glicko2",
        }
        if seed or rd is None:
            s = seed_from_external(rating, confidence=confidence)
            out["rd"] = s["rd"] if rd is None else float(rd)
            out["volatility"] = s["volatility"] if volatility is None else float(volatility)
            out["glicko2_seed"] = s
        else:
            out["rd"] = float(rd)
            out["volatility"] = float(volatility if volatility is not None else DEFAULT_VOL)
        return out

    if matches >= prefer_rackup_after_matches and rackup_f is not None:
        return _with_glicko(
            rackup_f,
            source="rackup_shared",
            confidence=0.9,
            rd=float(host_rd) if host_rd is not None else DEFAULT_RD,
            volatility=float(host_vol) if host_vol is not None else DEFAULT_VOL,
            seed=False,
        )

    # Priority for league systems when primary not set (§7.2.2)
    order = {
        "fargo": 1,
        "fargorate": 1,
        "fargo_rate": 1,
        "bca": 2,
        "apa": 3,
        "tap": 4,
        "vnea": 5,
    }

    if primary and league.get(primary) is not None:
        scale = (meta.get(primary) or {}).get("scale") or "auto"
        est = to_rackup(primary, league.get(primary), scale)
        return _with_glicko(
            est["rackup_rating_estimate"],
            source=f"primary:{primary}",
            confidence=est["confidence"],
            seed=True,
        )

    best = None
    best_key = (99, 99, "")
    for sys, val in (league.items() if isinstance(league, dict) else []):
        if val is None:
            continue
        m = meta.get(sys) or {}
        trusted = 0 if m.get("trusted") else 1
        pri = order.get(str(sys).lower(), 50)
        key = (trusted, pri, str(sys))
        if key < best_key:
            best_key = key
            scale = m.get("scale") or "auto"
            best = to_rackup(str(sys), val, scale)
            best["source"] = f"league:{sys}"

    if best:
        return _with_glicko(
            best["rackup_rating_estimate"],
            source=str(best.get("source")),
            confidence=float(best["confidence"]),
            seed=True,
        )

    if rackup_f is not None:
        return _with_glicko(
            rackup_f,
            source="rackup_shared",
            confidence=0.8,
            rd=float(host_rd) if host_rd is not None else DEFAULT_RD,
            volatility=float(host_vol) if host_vol is not None else DEFAULT_VOL,
            seed=host_rd is None,
        )

    return _with_glicko(
        DEFAULT_SEED,
        source="default_seed",
        confidence=0.2,
        seed=True,
    )
