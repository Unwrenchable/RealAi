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


def capability_card() -> str:
    """Deterministic, friendly operator card — live counts when catalogs load."""
    abilities = tools = agents = None
    try:
        from realai.ability_catalog import build_catalog

        abilities = len((build_catalog() or {}).get("abilities") or [])
    except Exception:
        pass
    try:
        from realai.v3_runtime_bridge import tools_catalog

        tools = len(tools_catalog() or [])
    except Exception:
        pass
    try:
        from realai.orchestration.v3_orchestrator import _load_agents

        agents = len(_load_agents() or [])
    except Exception:
        pass

    ab = str(abilities) if abilities is not None else "60+"
    tl = str(tools) if tools is not None else "100+"
    ag = str(agents) if agents is not None else "200+"

    return (
        "Hey — RealAI here, running local on this PC (Hive :8001).\n"
        "\n"
        "Talk normally. I can:\n"
        f"• Chat + code + repo work against C:\\RealAI-clean\n"
        f"• Run tools & abilities ({tl} tools · {ab} abilities · {ag} agents)\n"
        "• Speak aloud (Kokoro on this machine — toggle SPEAK)\n"
        "• Spin hive / multi-agent / self-heal / LoRA / recovery\n"
        "\n"
        "Easy starters (type as chat or click Ops):\n"
        "  /tools          — live catalog\n"
        "  /hive           — hive status + core roles\n"
        "  /heal           — self-heal status\n"
        "  /agents         — agent list\n"
        "  /coverage       — ability honesty map\n"
        "  /multi <task>   — planner → worker → critic\n"
        "  /nests          — nest orchestrators\n"
        "  /omnibrain      — omnibrain surface\n"
        "  /overseer       — overseer\n"
        "  /research …     — web research\n"
        "  /image …        — image generation\n"
        "  /speak …        — Kokoro TTS\n"
        "  /remember …     — memory\n"
        "  $ whoami        — real shell (never invents output)\n"
        "\n"
        "Or just ask in plain English — e.g. “list the repo”, “check Vulkan”, "
        "“run a multi-agent audit of apps/vscode”, “speak this out loud”.\n"
        "What do you want to do?"
    )


def try_talk_easy(text: str) -> Optional[Dict[str, Any]]:
    if not is_talk_easy(text):
        return None
    return {
        "surface": "talk",
        "tool": "talk_easy",
        "result": {"ok": True, "card": True, "text": capability_card()},
    }
