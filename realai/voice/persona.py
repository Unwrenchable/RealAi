"""Default Voice Engine persona for RealAI.

Used by tts_engine to turn agent text into speech-ready lines
for Kokoro, Fish Speech, XTTS, or Piper.
"""

from __future__ import annotations

from typing import Any, Dict

DEFAULT_PERSONA: Dict[str, Any] = {
    "id": "realai-voice-engine",
    "name": "RealAI Voice Engine",
    "style": "confident, warm, and clear",
    "pace": "tight for short replies, storytelling for long ones",
    "rules": [
        "Clear, concise, naturally paced speech.",
        "Human-like rhythm with micro-pauses at commas and periods.",
        "Emphasize important words lightly, never exaggerated.",
        "No robotic cadence, filler sounds, or fake artifacts.",
        "No system instructions, code, or metadata unless asked.",
        "Clean spoken text only.",
    ],
    "skip_speech_prefixes": (
        "```",
        "from ",
        "import ",
        "def ",
        "class ",
        "C:\\",
        "/",
    ),
}


def prepare_speech_text(text: str, persona: Dict[str, Any] = DEFAULT_PERSONA) -> str:
    """Strip markup and tighten text so a TTS model can read it cleanly."""
    if not text:
        return ""
    raw = text.replace("\r\n", "\n").strip()
    if raw.startswith("```"):
        return ""
    lines = []
    in_fence = False
    for line in raw.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith("#") and " " not in stripped[:3]:
            continue
        lines.append(line)
    spoken = " ".join(" ".join(lines).split())
    spoken = spoken.replace(" — ", ". ").replace(" – ", ", ")
    spoken = spoken.replace("*", "").replace("_", "")
    spoken = spoken.replace("`", "")
    prefixes = persona.get("skip_speech_prefixes") or ()
    for prefix in prefixes:
        if spoken.startswith(prefix):
            return ""
    return spoken.strip()
