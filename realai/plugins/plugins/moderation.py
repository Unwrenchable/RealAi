"""Chat moderation for RackUp — toxicity, harassment, money-match drama, sandbagging."""
from __future__ import annotations

import re
from typing import Any

from plugins.rackup_coach.types import PlayerProfile


# Pattern banks (provider-side heuristics — host applies actions)
_HARASS = [
    r"\bkill\s+yourself\b",
    r"\bkys\b",
    r"\b(idiot|moron|retard|stupid\s+bitch|fuck\s+you)\b",
    r"\b(racist|slur)\b",
]
_TOXIC = [
    r"\b(trash|garbage|noob|ez\s*clap|get\s+good)\b",
    r"\b(uninstall|delete\s+the\s+app)\b",
    r"\byou\s+suck\b",
]
_MONEY_DRAMA = [
    r"\b(scam|scammer|ripped?\s+me\s+off|won'?t\s+pay|didn'?t\s+pay)\b",
    r"\b(money\s*match|wager|bet\s+for\s+cash|\$\d+)\b.*\b(lie|liar|cheat)\b",
    r"\b(paypal|venmo|cashapp).*\b(scam|ghost|block)\b",
]
_SANDBAG = [
    r"\b(sandbag|sand\s*bagg(?:er|ing)?|hustl(?:e|er|ing)\b)",
    r"\b(fake\s+rating|smurf|smurfing|throwing\s+games|tanking)\b",
    r"\b(you'?re\s+not\s+a\s+\d+|rated\s+\d+\s+playing\s+like)\b",
]
_THREAT = [
    r"\b(i'?ll\s+find\s+you|come\s+outside|beat\s+your\s+ass)\b",
    r"\b(dox|doxx|swat)\b",
]


def _scan(patterns: list[str], text: str) -> list[str]:
    hits = []
    for p in patterns:
        if re.search(p, text, re.I):
            hits.append(p)
    return hits


def moderate_message(
    text: str,
    *,
    player: PlayerProfile | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Analyze a chat message; return structured moderation decision."""
    context = context or {}
    raw = (text or "").strip()
    lower = raw.lower()

    categories: dict[str, list[str]] = {
        "harassment": _scan(_HARASS, lower),
        "toxicity": _scan(_TOXIC, lower),
        "money_match_drama": _scan(_MONEY_DRAMA, lower),
        "sandbagging_accusation": _scan(_SANDBAG, lower),
        "threat": _scan(_THREAT, lower),
    }
    # Caps / spam
    caps_ratio = (sum(1 for c in raw if c.isupper()) / max(len(raw), 1)) if raw else 0
    if caps_ratio > 0.7 and len(raw) > 12:
        categories.setdefault("spam_shouting", []).append("excessive_caps")
    if len(re.findall(r"(.)\1{5,}", lower)) > 0:
        categories.setdefault("spam_shouting", []).append("char_repeat")

    active = {k: v for k, v in categories.items() if v}
    severity = 0
    if active.get("threat") or active.get("harassment"):
        severity = 5
    elif active.get("money_match_drama"):
        severity = 4
    elif active.get("sandbagging_accusation"):
        severity = 3
    elif active.get("toxicity"):
        severity = 2
    elif active.get("spam_shouting"):
        severity = 1

    # Escalation from context (prior flags from host)
    prior = int(context.get("prior_flags") or 0)
    if prior >= 2:
        severity = min(5, severity + 1)

    action = "allow"
    if severity >= 5:
        action = "block_and_escalate"
    elif severity == 4:
        action = "hold_for_review"
    elif severity == 3:
        action = "warn_and_flag"
    elif severity == 2:
        action = "warn"
    elif severity == 1:
        action = "soft_filter"

    guidance = {
        "allow": "Message OK for public chat.",
        "soft_filter": "Consider rate-limit or nudge for tone.",
        "warn": "Issue a civility warning; keep message if policy allows.",
        "warn_and_flag": "Warn user; flag for trust & safety (rating integrity).",
        "hold_for_review": "Hold money-related dispute for human review.",
        "block_and_escalate": "Block delivery; escalate immediately.",
    }[action]

    coach_redirect = None
    if active.get("sandbagging_accusation"):
        coach_redirect = (
            "Redirect players to rating appeal flow; offer objective session stats "
            "instead of public accusations."
        )
    if active.get("money_match_drama"):
        coach_redirect = (
            "Suggest in-app escrow / official money-match channel; freeze public thread."
        )

    channel = str(context.get("channel") or "")
    is_roc_chat = channel.lower().startswith("roc") or bool(
        context.get("roc_league_id") or context.get("session_id")
    )
    # Money language: escalate prize/ledger drama inside ROC sessions
    if is_roc_chat and active.get("money_match_drama"):
        severity = max(severity, 4)
        if severity >= 5:
            action = "block_and_escalate"
        elif severity == 4:
            action = "hold_for_review"
        coach_redirect = (
            coach_redirect
            or "ROC money disputes: freeze thread; operator + ledger history — never public accusations."
        )

    return {
        "text_preview": raw[:200],
        "player_id": player.player_id if player else context.get("player_id"),
        "clean": severity == 0,
        "severity": severity,
        "severity_label": ["none", "low", "moderate", "elevated", "high", "critical"][severity],
        "action": action,
        "guidance": guidance,
        "categories": {k: True for k in active},
        "matched_patterns": {k: len(v) for k, v in active.items()},
        "coach_redirect": coach_redirect,
        "organs_hint": ["amygdala", "guardian", "prefrontal"],
        "policy_tags": list(active.keys()),
        "roc": {
            "is_roc": is_roc_chat,
            "roc_league_id": context.get("roc_league_id"),
            "session_id": context.get("session_id"),
            "channel": channel or None,
            "note": "All ROC chat paths should run moderation before fan-out",
        },
    }


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    text = str(payload.get("text") or payload.get("message") or payload.get("content") or "")
    ctx = dict(payload.get("context") or {})
    # Flatten ROC ids into moderation context
    for k in ("roc_league_id", "session_id", "season_id", "channel", "match_id", "format"):
        if payload.get(k) and k not in ctx:
            ctx[k] = payload[k]
    return moderate_message(text, player=player, context=ctx or payload)
