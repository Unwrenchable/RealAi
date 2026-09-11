"""
ROC — Rack of Champions awareness for RealAI (provider-side).

Source of truth: ROC_SYSTEM_DESIGN.md
RackUp owns: leagues, sessions, ledger (45/35/20), payouts, UI.
RealAI owns: continuous rating math, validation, coaching, convert, matchmaking.

No money/ledger mutation lives here.
"""
from __future__ import annotations

from typing import Any, Optional

# --- Format rollout order (exact) ---
FORMAT_SINGLES = "SINGLES"
FORMAT_SCOTCH_DOUBLES = "SCOTCH_DOUBLES"
FORMAT_SCOTCH_JJ = "SCOTCH_JJ"
FORMAT_TEAMS_5 = "TEAMS_5"

FORMATS_ORDERED = (
    FORMAT_SINGLES,
    FORMAT_SCOTCH_DOUBLES,
    FORMAT_SCOTCH_JJ,
    FORMAT_TEAMS_5,
)

FORMAT_DISPLAY = {
    FORMAT_SINGLES: "Singles",
    FORMAT_SCOTCH_DOUBLES: "Scotch Doubles League",
    FORMAT_SCOTCH_JJ: "Scotch Jack & Jill",
    FORMAT_TEAMS_5: "Teams of 5",
}

# Game styles (day one)
GAME_STYLES = (
    "eight_ball",
    "nine_ball",
    "ten_ball",
    "one_pocket",
    "pyramid",
)

# Roles
ROLES = ("OPERATOR", "ADMIN", "PLAYER", "CAPTAIN", "PLATFORM")

# Default product seed — Intermediate • 500
DEFAULT_ROC_SEED = 500

# Soft product range for continuous ROC/RackUp ladder (Fargo-like family)
ROC_RATING_MIN = 100
ROC_RATING_MAX = 1200  # headroom above Elite; clamp only

# Locked display-band cuts (§7.1.2)
# Under 400 Novice | 400–499 Intermediate | 500–599 Advanced | 600–699 Expert | 700+ Elite


def normalize_format(raw: Any) -> Optional[str]:
    if raw is None or raw == "":
        return None
    s = str(raw).strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "SINGLES": FORMAT_SINGLES,
        "SINGLE": FORMAT_SINGLES,
        "1V1": FORMAT_SINGLES,
        "SCOTCH_DOUBLES": FORMAT_SCOTCH_DOUBLES,
        "SCOTCHDOUBLES": FORMAT_SCOTCH_DOUBLES,
        "DOUBLES": FORMAT_SCOTCH_DOUBLES,
        "SCOTCH": FORMAT_SCOTCH_DOUBLES,
        "SCOTCH_JJ": FORMAT_SCOTCH_JJ,
        "SCOTCH_JACK_AND_JILL": FORMAT_SCOTCH_JJ,
        "SCOTCH_JACK_JILL": FORMAT_SCOTCH_JJ,
        "JACK_AND_JILL": FORMAT_SCOTCH_JJ,
        "JJ": FORMAT_SCOTCH_JJ,
        "TEAMS_5": FORMAT_TEAMS_5,
        "TEAMS": FORMAT_TEAMS_5,
        "TEAM_OF_5": FORMAT_TEAMS_5,
        "TEAMSOF5": FORMAT_TEAMS_5,
        "5MAN": FORMAT_TEAMS_5,
    }
    if s in aliases:
        return aliases[s]
    if s in FORMATS_ORDERED:
        return s
    return None


def format_config(fmt: str | None) -> dict[str, Any]:
    """Canonical format_config by format (§1.6)."""
    f = normalize_format(fmt) or FORMAT_SINGLES
    configs = {
        FORMAT_SINGLES: {
            "pairing": "INDIVIDUAL",
            "gender_policy": "OPEN",
            "rating_impact": "INDIVIDUAL",
            "payment_entity": "USER",
            "competitor_type": "USER",
        },
        FORMAT_SCOTCH_DOUBLES: {
            "pairing": "FIXED_PARTNER",
            "scotch_rules": "ALTERNATE_SHOT",
            "partner_change_policy": "LOCKED_AFTER_WEEK_1",
            "rating_impact": "BOTH_PARTNERS",
            "payment_entity": "PARTNERSHIP",
            "default_payout_split": "EQUAL",
            "competitor_type": "TEAM",
        },
        FORMAT_SCOTCH_JJ: {
            "pairing": "MIXED_GENDER",
            "require_gender_declared": True,
            "pair_rule": "ONE_M_ONE_F",
            "scotch_rules": "ALTERNATE_SHOT",
            "rating_impact": "BOTH_PARTNERS",
            "payment_entity": "PARTNERSHIP",
            "default_payout_split": "EQUAL",
            "competitor_type": "TEAM",
        },
        FORMAT_TEAMS_5: {
            "roster_size": 5,
            "min_active_per_session": 3,
            "max_roster": 7,
            "lineup_deadline_minutes": 30,
            "match_model": "BEST_OF_N_SINGLES",
            "rating_impact": "INDIVIDUAL_MATCHES_PLUS_TEAM_STANDINGS",
            "payment_entity": "TEAM",
            "captain_required": True,
            "default_payout_split": "EQUAL_CHECKED_IN",
            "competitor_type": "TEAM",
        },
    }
    out = dict(configs[f])
    out["format"] = f
    out["display_name"] = FORMAT_DISPLAY[f]
    return out


def rating_subjects_for_match(
    fmt: str | None,
    *,
    player_ids: list[str] | None = None,
    board_player_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Who receives rating_update after a match (§7.1.4).
    Host still calls rating_update per user; this documents subjects.
    """
    f = normalize_format(fmt) or FORMAT_SINGLES
    cfg = format_config(f)
    impact = cfg["rating_impact"]
    ids = list(player_ids or [])
    board = list(board_player_ids or ids)

    if impact == "INDIVIDUAL":
        subjects = ids
        note = "Both individual players receive rating_update."
    elif impact == "BOTH_PARTNERS":
        subjects = ids  # full player_ids_json for both partnerships
        note = "Both partners on each side receive rating_update (player_ids_json)."
    else:  # INDIVIDUAL_MATCHES_PLUS_TEAM_STANDINGS
        subjects = board
        note = (
            "Each user on a board match they played gets rating_update; "
            "team standings are separate (RackUp)."
        )
    return {
        "format": f,
        "rating_impact": impact,
        "subject_player_ids": subjects,
        "note": note,
        "provider_does_not_persist": True,
    }


def extract_roc_context(
    player: Any = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Pull ROC league/session/format context from player + payload.
    Accepts nested payload.roc or flat keys.
    """
    payload = payload or {}
    roc_block = dict(payload.get("roc") or {})
    # Player may be PlayerProfile or dict
    if hasattr(player, "to_dict"):
        pd = player.to_dict()
    elif isinstance(player, dict):
        pd = player
    else:
        pd = {}

    def _first(*keys: str, default: Any = None) -> Any:
        for k in keys:
            if k in roc_block and roc_block[k] not in (None, ""):
                return roc_block[k]
            if k in payload and payload[k] not in (None, ""):
                return payload[k]
            if k in pd and pd[k] not in (None, ""):
                return pd[k]
        return default

    fmt = normalize_format(_first("format", "roc_format", "season_format"))
    game_style = _first("game_style", "game", "discipline") or pd.get("discipline")
    ctx = {
        "roc_league_id": _first("roc_league_id", "league_id"),
        "season_id": _first("season_id"),
        "session_id": _first("session_id"),
        "match_id": _first("match_id", "roc_match_id"),
        "format": fmt,
        "format_display": FORMAT_DISPLAY.get(fmt or "", None),
        "format_config": format_config(fmt) if fmt else None,
        "game_style": game_style,
        "competitor_type": _first("competitor_type"),
        "competitor_id": _first("competitor_id"),
        "team_id": _first("team_id"),
        "board_index": _first("board_index", "board"),
        "player_ids_json": list(
            _first("player_ids_json", "player_ids", default=[]) or []
        ),
        "require_realai_validate": bool(
            _first("require_realai_validate", default=True)
        ),
        "is_roc": bool(
            fmt
            or _first("roc_league_id")
            or _first("session_id")
            or roc_block
            or str(payload.get("channel") or "").lower().startswith("roc")
            or str((payload.get("context") or {}).get("channel") or "")
            .lower()
            .startswith("roc")
        ),
    }
    # competitor_type from format if missing
    if not ctx["competitor_type"] and ctx["format_config"]:
        ctx["competitor_type"] = ctx["format_config"].get("competitor_type")
    return ctx


def format_coaching_notes(fmt: str | None, game_style: str | None = None) -> list[str]:
    """Session-aware coaching tips by ROC format (§7.3.4)."""
    f = normalize_format(fmt)
    notes: list[str] = []
    gs = (game_style or "").lower()
    if f == FORMAT_SINGLES:
        notes.append(
            "Singles: own every decision — tempo, safety exchanges, and table speed "
            "are entirely on you."
        )
    elif f in (FORMAT_SCOTCH_DOUBLES, FORMAT_SCOTCH_JJ):
        notes.append(
            "Scotch alternate-shot: communicate leave intent before you shoot; "
            "your partner inherits your shape."
        )
        notes.append(
            "Prefer natural shape that leaves a comfortable angle for the next shooter."
        )
        if f == FORMAT_SCOTCH_JJ:
            notes.append(
                "Jack & Jill: mixed partnership — agree on aggression early; "
                "avoid surprise hero pots."
            )
    elif f == FORMAT_TEAMS_5:
        notes.append(
            "Teams of 5 board match: play your individual race cleanly; "
            "team standings are separate from your continuous rating."
        )
        notes.append(
            "Captain lineups matter for standings — your rating only moves from boards you play."
        )
    if gs == "pyramid":
        notes.append(
            "Pyramid: classical points on American table — count to target, protect the 1-ball (11)."
        )
    elif gs in ("nine_ball", "ten_ball"):
        notes.append("Race format: protect the hill; don't force early low-percentage outs.")
    elif gs == "one_pocket":
        notes.append("One Pocket: patience and bank safety win leagues more than hero banks.")
    elif gs == "eight_ball":
        notes.append("8-Ball: clear problem balls first; call the 8 pocket every time.")
    return notes


def scotch_rules_checks(payload: dict[str, Any] | None = None) -> list[str]:
    """Soft validation warnings for scotch formats (host still owns hard rules)."""
    payload = payload or {}
    warnings: list[str] = []
    fmt = normalize_format(payload.get("format") or (payload.get("roc") or {}).get("format"))
    if fmt not in (FORMAT_SCOTCH_DOUBLES, FORMAT_SCOTCH_JJ):
        return warnings
    pids = payload.get("player_ids_json") or payload.get("player_ids") or []
    if len(pids) not in (0, 4) and len(pids) not in (2, 4):
        # 2 per side = 4 users typical; allow 2 if only one side reported
        if len(pids) < 2:
            warnings.append("scotch match expects partner player_ids for rating impact")
    if fmt == FORMAT_SCOTCH_JJ and payload.get("require_gender_declared", True):
        if not payload.get("gender_ok") and not payload.get("skip_gender_check"):
            warnings.append(
                "Scotch JJ seasons require declared gender pairing (ONE_M_ONE_F) — host should verify"
            )
    return warnings


def teams5_rules_checks(payload: dict[str, Any] | None = None) -> list[str]:
    payload = payload or {}
    warnings: list[str] = []
    fmt = normalize_format(payload.get("format") or (payload.get("roc") or {}).get("format"))
    if fmt != FORMAT_TEAMS_5:
        return warnings
    if payload.get("board_index") is None and not payload.get("board"):
        warnings.append("Teams of 5: set board_index for individual board matches")
    return warnings


def roc_provider_boundary() -> dict[str, Any]:
    """What RealAI never owns inside ROC."""
    return {
        "owns_rating_math": True,
        "owns_league_validate": True,
        "owns_coach_sotd_moderation_mm": True,
        "owns_money_audit": True,
        "owns_ledger": False,
        "owns_payouts": False,
        "owns_stripe": False,
        "owns_ui": False,
        "authorize_payout": False,
        "default_split_reference_only": {"players_fund_bps": 4500, "operator_bps": 3500, "platform_bps": 2000},
        "note": "45/35/20 split and session auto-payouts are RackUp ledger only. RealAI audits snapshots only.",
        "money_audit_abilities": ["ledger_audit", "payout_sanity", "money_anomaly"],
        "finalize_order": [
            "score_report_dual_confirm",
            "league_validate",
            "persist_match_if_valid",
            "rating_update_per_player_ids_json",
            "refresh_payout_projections_rackup",
            "ledger_audit_before_auto_payout",
            "payout_sanity_before_auto_payout",
            "rackup_auto_payout_if_audit_ok",
            "optional_coach_non_blocking",
        ],
    }


def attach_roc_to_result(
    result: dict[str, Any],
    player: Any = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Embed roc context + coaching notes without overwriting ability fields."""
    if not isinstance(result, dict):
        return result
    ctx = extract_roc_context(player, payload)
    if not ctx.get("is_roc") and not ctx.get("format"):
        # Still expose empty-safe metadata for host discoverability
        result.setdefault("roc", {"is_roc": False})
        return result
    result["roc"] = {
        "is_roc": True,
        "roc_league_id": ctx.get("roc_league_id"),
        "season_id": ctx.get("season_id"),
        "session_id": ctx.get("session_id"),
        "match_id": ctx.get("match_id"),
        "format": ctx.get("format"),
        "format_display": ctx.get("format_display"),
        "format_config": ctx.get("format_config"),
        "game_style": ctx.get("game_style"),
        "competitor_type": ctx.get("competitor_type"),
        "provider_boundary": {
            "owns_ledger": False,
            "owns_rating_math": True,
        },
    }
    tips = format_coaching_notes(ctx.get("format"), ctx.get("game_style"))
    if tips and "format_coaching_notes" not in result:
        result["format_coaching_notes"] = tips
    return result
