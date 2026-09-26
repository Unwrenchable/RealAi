"""Natural-talk shortcuts for RealAI Console — capability cards without waiting on GGUF.

Makes “hey / what can you do / help” feel like talking to a real operator,
not a generic assistant, even when the local model drifts.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

_HELP_RE = re.compile(
    r"(?i)^\s*("
    r"hey|hi|hello|yo|sup|"
    r"what can you (do|help (me )?with)|"
    r"what do you (do|offer)|"
    r"help( me)?(\s+please)?|"
    r"how (do i|can i) (use|talk to|work with) (you|this|realai)|"
    r"who are you|"
    r"capabilities?|"
    r"show me (what you can do|tools|abilities)|"
    r"getting started|"
    r"what('?s| is) (up|new)"
    r")\b.*$"
)


def is_talk_easy(text: str) -> bool:
    raw = (text or "").strip()
    if not raw or len(raw) > 160:
        return False
    if raw.startswith("/") or raw.startswith("$"):
        return False
    return bool(_HELP_RE.match(raw))


def greeting_card() -> str:
    """Short hello. Not a capability list and not a slash manual."""
    return (
        "Hey — RealAI, local on this PC.\n"
        "Just talk. I'll open files, fix things, and check my work when you ask.\n"
        "What do you need?"
    )


def capability_card() -> str:
    """Greeting used when a model reply collapses to generic assistant filler.

    Capability and status asks go through ``format_live_manifest`` instead
    of a canned tool/ability/agent count.
    """
    return greeting_card()


def try_talk_easy(text: str) -> Optional[Dict[str, Any]]:
    if not is_talk_easy(text):
        return None
    raw = (text or "").strip()
    try:
        from realai.bot.live_manifest import format_live_manifest, is_manifest_turn

        if is_manifest_turn(raw):
            card = format_live_manifest(raw)
        else:
            card = greeting_card()
    except Exception:
        card = greeting_card()
    return {
        "surface": "talk",
        "tool": "talk_easy",
        "result": {"ok": True, "card": True, "text": card},
    }
