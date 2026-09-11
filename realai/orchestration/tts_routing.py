"""Voice-aware orchestrator routing.

Sends speech-ready replies through the Voice Engine and keeps
code, logs, and system text on the text path. Import is lazy.
Does not start Craft, heal, or servers.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

VOICE_ROUTES: Dict[str, str] = {
    "voice": "realai.voice.tts_engine",
    "persona": "realai.voice.persona",
    "tts": "realai.orchestration.tts_routing",
    "loader": "realai.models.loader",
    "amd": "realai.config.amd_inference",
}

SPEAK_INTENTS = frozenset(
    ("chat", "reply", "speak", "voice", "status", "greeting", "summary")
)
TEXT_ONLY_INTENTS = frozenset(
    ("code", "diff", "log", "heal", "dispatch", "train", "shell", "reconstruct")
)


def should_speak(intent: str = "chat", text: str = "") -> bool:
    kind = (intent or "chat").strip().lower()
    if kind in TEXT_ONLY_INTENTS:
        return False
    blob = (text or "").lstrip()
    if blob.startswith("```") or blob.startswith("C:\\") or blob.startswith("def "):
        return False
    return kind in SPEAK_INTENTS or kind == "chat"


def route_reply(text: str, intent: str = "chat") -> Dict[str, Any]:
    """Pick text vs speech path. Does not call TTS until speak=True is consumed."""
    speak = should_speak(intent, text)
    route = {
        "intent": intent,
        "speak": speak,
        "module": VOICE_ROUTES["voice"] if speak else "realai.orchestration.orchestrator",
        "text": text,
        "audio": None,
    }
    if not speak:
        return route
    try:
        from realai.voice.tts_engine import get_tts_engine
        from realai.voice.persona import prepare_speech_text

        spoken = prepare_speech_text(text)
        route["text"] = spoken
        if spoken:
            route["audio"] = get_tts_engine().synthesize(spoken, prepare=False)
    except Exception as exc:
        route["speak"] = False
        route["error"] = str(exc)
    return route


def hive_voice_entry() -> Dict[str, str]:
    """Extra hive_router keys without mutating hive_router.py."""
    return dict(VOICE_ROUTES)
