"""Unified Player Card sync — APA + Fargo + RackUp (parallel fields).

Nest owns Fargo HTTP (read-only). RealAI consumes snapshots and returns
``unified_player_card.v1``. Never invents Fargo, never LMS-submits, never
copies leagues v2 (0–3000) onto ROC Glicko ``users.rating``.
"""
from __future__ import annotations

import os
from typing import Any

from plugins.rackup_coach.glicko2 import DEFAULT_RD, DEFAULT_VOL
from plugins.rackup_coach.leagues import (
    convert_rating,
    display_band,
    format_rating_chip,
)
from plugins.rackup_coach.types import PlayerProfile

SCHEMA = "unified_player_card.v1"

# Read-only Fargo lookups Nest owns (same URLs if RealAI optionally fetches).
FARGO_SEARCH_URL = "https://dashboard.fargorate.com/api/indexSearch"
FARGO_PLAYER_URL = "https://dashboard.fargorate.com/api/indexPlayer"

APA_TOKEN_ENV = ("APA_MEMBER_TOKEN", "RACKUP_APA_TOKEN", "APA_TOKEN")

# Leagues v2 0–3000 centers (display/import ONLY — not ROC 500-band).
# Mirrors RACKUP_GAME_KNOWLEDGE_AND_AI_CONTRACT.md §C.3
_APA_TO_LEAGUES_V2 = {
    1: 400,
    2: 700,
    3: 950,
    4: 1200,
    5: 1500,
    6: 1850,
    7: 2200,
    8: 2500,
    9: 2700,
}

CARD_KEYS = (
    "identity",
    "roc_glicko",
    "fargo",
    "rackup_rate_shadow",
    "apa_sl",
    "bca",
    "tap",
    "leagues_v2",
    "sources",
    "matchmaking",
)

POLICY = {
    "schema": SCHEMA,
    "lms_submit": False,
    "heal": False,
    "fake_match_reports": False,
    "invent_fargo": False,
    "apa_requires_token": True,
    "fargo_http_owner": "nest",
    "canonical_competitive": "roc_glicko",
    "leagues_v2_overwrites_roc": False,
}


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(payload or {})
    token_ok = _apa_token_present(payload)
    fargo = _fargo_block(payload, player)
    apa_sl, apa_source = _apa_sl_block(payload, player, token_ok)
    bca = _manual_league_block(payload, player, "bca")
    tap = _manual_league_block(payload, player, "tap")
    roc = _roc_glicko_block(player, payload)
    leagues_v2 = _leagues_v2_block(payload, apa_sl)
    shadow = _shadow_rackup_rate(fargo, apa_sl, bca, tap)
    identity = _identity(player, payload, fargo)
    notes = _matchmaking_notes(roc, fargo, shadow, apa_sl, leagues_v2)
    apa_entry = "apa_lms" if token_ok and apa_source == "apa_lms" else (
        "manual" if apa_sl is not None else "missing"
    )
    apa_sync = "token_ok" if token_ok else "skipped_no_token"

    card = {
        "identity": identity,
        "roc_glicko": roc,
        "fargo": fargo,
        "rackup_rate_shadow": shadow,
        "apa_sl": apa_sl,
        "bca": bca,
        "tap": tap,
        "leagues_v2": leagues_v2,
        "sources": {
            "fargo": {
                "http_owner": "nest",
                "read_only": True,
                "endpoints": {
                    "search": FARGO_SEARCH_URL,
                    "player": FARGO_PLAYER_URL,
                },
                "fetch_in_realai": False,
                "status": fargo.get("status"),
            },
            "apa": {
                "sync": apa_sync,
                "entry": apa_entry,
                "requires_token": True,
                "token_present": token_ok,
            },
            "bca": {"entry": "manual" if bca is not None else "missing"},
            "tap": {"entry": "manual" if tap is not None else "missing"},
            "rackup": {"canonical": "roc_glicko", "storage": "users.rating"},
        },
        "matchmaking": {
            "competitive_input": "roc_glicko",
            "ignore_for_roc_ladder": [
                "leagues_v2",
                "fargo",
                "apa_sl",
                "bca",
                "tap",
                "rackup_rate_shadow",
            ],
            "fargo_read_only": True,
            "shadow_may_inform_mixed_league_confidence": True,
            "widen_when_rd_high": True,
            "notes": notes,
        },
    }

    return {
        "schema": SCHEMA,
        "card": card,
        "policy": dict(POLICY),
        "notes": notes,
        "boundary": {
            "nest": "Fargo HTTP + APA token HTTP + persist card + write users.rating after rating_update",
            "realai": "Assemble card, ROC Glicko math, shadow estimate, matchmaking notes",
            "never": [
                "lms_submit",
                "heal",
                "invent_fargo",
                "fake_match_reports",
                "overwrite_roc_with_leagues_v2",
            ],
        },
    }


def _identity(
    player: PlayerProfile,
    payload: dict[str, Any],
    fargo: dict[str, Any],
) -> dict[str, Any]:
    name = (
        payload.get("name")
        or payload.get("player_name")
        or player.display_name
        or ""
    )
    fargo_id = (
        payload.get("fargo_id")
        or payload.get("fargoId")
        or fargo.get("player_id")
        or None
    )
    apa_member_id = payload.get("apa_member_id") or payload.get("apaMemberId") or None
    return {
        "player_id": player.player_id,
        "display_name": player.display_name or str(name or ""),
        "fargo_id": _str_or_none(fargo_id),
        "apa_member_id": _str_or_none(apa_member_id),
        "name_query": str(name or player.display_name or "").strip() or None,
    }


def _roc_glicko_block(player: PlayerProfile, payload: dict[str, Any]) -> dict[str, Any]:
    rating = player.rating
    if rating is None:
        rating = 500.0
    rd = float(payload.get("rd") or getattr(player, "rd", None) or DEFAULT_RD)
    vol = float(
        payload.get("volatility")
        or getattr(player, "volatility", None)
        or DEFAULT_VOL
    )
    matches = int(payload.get("matches_played_rackup") or player.matches_played_rackup or 0)
    r = float(rating)
    return {
        "canonical": True,
        "storage": "users.rating",
        "rating": r,
        "rd": rd,
        "volatility": vol,
        "rating_chip": format_rating_chip(r),
        "band_label": display_band(r),
        "ladder": "roc_glicko2",
        "algorithm": "glicko2_v1",
        "math_owner": "realai.rating_update",
        "seed": 500,
        "scale": "roc_500_band",
        "matches_played_rackup": matches,
    }


def _fargo_block(payload: dict[str, Any], player: PlayerProfile) -> dict[str, Any]:
    """Never invent. Only Nest snapshot / explicit fargo id+rating on the envelope."""
    snap = _first_dict(
        payload.get("fargo"),
        (payload.get("sources") or {}).get("fargo") if isinstance(payload.get("sources"), dict) else None,
        payload.get("fargo_snapshot"),
    )
    missing = {
        "status": "missing",
        "read_only": True,
        "invented": False,
        "player_id": _str_or_none(payload.get("fargo_id") or payload.get("fargoId")),
        "rating": None,
        "robustness": None,
        "source": None,
    }
    if snap:
        rating = _num(snap.get("rating") if snap.get("rating") is not None else snap.get("effectiveRating"))
        if rating is None:
            return {**missing, "status": "incomplete_snapshot", "source": "nest_snapshot"}
        return {
            "status": "present",
            "read_only": True,
            "invented": False,
            "player_id": _str_or_none(
                snap.get("playerId") or snap.get("player_id") or payload.get("fargo_id")
            ),
            "rating": rating,
            "robustness": _num(snap.get("robustness") or snap.get("robustnessRating")),
            "source": "nest_snapshot",
        }
    # league_ratings.fargo is host-supplied Fargo, still not invented — but only
    # if explicitly keyed as fargo (never derived from APA/ROC).
    lr = player.league_ratings or {}
    if isinstance(lr, dict) and lr.get("fargo") is not None:
        rating = _num(lr.get("fargo"))
        if rating is not None:
            return {
                "status": "present",
                "read_only": True,
                "invented": False,
                "player_id": _str_or_none(payload.get("fargo_id")),
                "rating": rating,
                "robustness": None,
                "source": "host_league_ratings",
            }
    return missing


def _apa_sl_block(
    payload: dict[str, Any],
    player: PlayerProfile,
    token_ok: bool,
) -> tuple[int | None, str | None]:
    snap = _first_dict(
        payload.get("apa"),
        (payload.get("sources") or {}).get("apa") if isinstance(payload.get("sources"), dict) else None,
    )
    sl = _apa_sl_value(
        payload.get("apa_sl"),
        payload.get("apa_skill_level"),
        (snap or {}).get("skill_level") if snap else None,
        (snap or {}).get("apa_sl") if snap else None,
        (player.league_ratings or {}).get("apa") if isinstance(player.league_ratings, dict) else None,
    )
    if token_ok and snap:
        return sl, "apa_lms"
    if sl is not None:
        return sl, "manual"
    return None, None


def _manual_league_block(
    payload: dict[str, Any],
    player: PlayerProfile,
    system: str,
) -> dict[str, Any] | None:
    raw = payload.get(system)
    if raw is None and isinstance(player.league_ratings, dict):
        raw = player.league_ratings.get(system)
    if raw is None:
        return None
    if isinstance(raw, dict):
        value = raw.get("value") if raw.get("value") is not None else raw.get("rating")
        scale = str(raw.get("scale") or "auto")
    else:
        value = raw
        meta = player.league_ratings_meta or {}
        scale = str((meta.get(system) or {}).get("scale") or "auto")
    if value is None or value == "":
        return None
    return {"value": value, "scale": scale, "entry": "manual"}


def _leagues_v2_block(payload: dict[str, Any], apa_sl: int | None) -> dict[str, Any]:
    raw_v2 = payload.get("leagues_v2")
    nested = raw_v2.get("value") if isinstance(raw_v2, dict) else raw_v2
    value = _num(
        payload.get("leagues_v2_rating")
        or payload.get("unified_0_3000")
        or nested
    )
    estimated = False
    if value is None and apa_sl is not None:
        value = float(_APA_TO_LEAGUES_V2.get(int(apa_sl), 400 + int(apa_sl) * 250))
        estimated = True
        value = max(0.0, min(3000.0, value))
    return {
        "scale": "0_3000",
        "value": value,
        "estimated_from_apa_sl": estimated,
        "overwrites_roc": False,
        "do_not_write_to_users_rating": True,
        "note": "Parallel import/display continuum. Never copy onto ROC Glicko users.rating.",
    }


def _shadow_rackup_rate(
    fargo: dict[str, Any],
    apa_sl: int | None,
    bca: dict[str, Any] | None,
    tap: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if fargo.get("status") == "present" and fargo.get("rating") is not None:
        v = float(fargo["rating"])
        return {
            "value": int(round(v)),
            "scale": "roc_500_band",
            "alongside": "fargo",
            "does_not_overwrite_fargo": True,
            "does_not_overwrite_roc_glicko": True,
            "method": "fargo_passthrough",
        }
    # Convert onto ROC 500-band only — never leagues v2.
    for system, block, scale_default in (
        ("apa", {"value": apa_sl} if apa_sl is not None else None, "skill_1_9"),
        ("bca", bca, "auto"),
        ("tap", tap, "auto"),
    ):
        if not block or block.get("value") is None:
            continue
        est = convert_rating(
            {
                "from_system": system,
                "from_value": block.get("value"),
                "from_scale": block.get("scale") or scale_default,
            }
        )
        return {
            "value": est.get("rackup_rating_estimate"),
            "scale": "roc_500_band",
            "alongside": "fargo",
            "does_not_overwrite_fargo": True,
            "does_not_overwrite_roc_glicko": True,
            "method": "rating_convert_roc",
            "from_system": system,
            "confidence": est.get("confidence"),
        }
    return None


def _matchmaking_notes(
    roc: dict[str, Any],
    fargo: dict[str, Any],
    shadow: dict[str, Any] | None,
    apa_sl: int | None,
    leagues_v2: dict[str, Any],
) -> list[str]:
    notes = [
        "Competitive matchmaking uses roc_glicko (users.rating + rd) only.",
        "leagues_v2 0–3000 is a parallel display/import scale — do not overwrite ROC.",
        "Fargo is read-only; never invent a Fargo rating.",
        "Do not submit matches to APA / Fargo LMS / TAP / BCA.",
    ]
    if roc.get("matches_played_rackup", 0) >= 5:
        notes.append("ROC history exists — do not reseed users.rating from shadow or leagues.")
    elif shadow:
        notes.append(
            "Thin ROC history: rackup_rate_shadow may inform mixed-league confidence, not the official ladder."
        )
    if fargo.get("status") == "missing":
        notes.append("Fargo snapshot absent — card.fargo.rating is null (not estimated).")
    if apa_sl is None:
        notes.append("No APA SL on card (token LMS skipped or host did not supply one).")
    if leagues_v2.get("value") is not None:
        notes.append(
            f"leagues_v2.value={leagues_v2['value']} must not be written to users.rating."
        )
    rd = float(roc.get("rd") or DEFAULT_RD)
    if rd >= 150:
        notes.append(f"High Glicko RD ({rd:.0f}): widen matchmaking windows.")
    return notes


def _apa_token_present(payload: dict[str, Any]) -> bool:
    if payload.get("apa_token") or payload.get("apa_member_token"):
        return True
    hint = payload.get("apa_token_hint")
    if hint not in (None, False, "", 0, "0"):
        # Explicit hint: env token still required for LMS path.
        return _env_apa_token()
    return _env_apa_token()


def _env_apa_token() -> bool:
    for key in APA_TOKEN_ENV:
        val = os.environ.get(key)
        if val:
            return True
    return False


def _apa_sl_value(*candidates: Any) -> int | None:
    for raw in candidates:
        if raw is None or raw == "":
            continue
        try:
            sl = int(float(raw))
        except (TypeError, ValueError):
            continue
        if 1 <= sl <= 9:
            return sl
    return None


def _first_dict(*candidates: Any) -> dict[str, Any] | None:
    for c in candidates:
        if isinstance(c, dict) and c:
            return c
    return None


def _num(raw: Any) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _str_or_none(raw: Any) -> str | None:
    if raw is None or raw == "":
        return None
    return str(raw)
