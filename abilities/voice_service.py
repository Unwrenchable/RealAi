"""Shared local voice ability: speak/health via realai.voice_service (Voice Lab :8890 if up, else canonical engine).

Hive (ability.voice_service through the registry fall-through), agents (import), CLI (python -m realai.voice_service)
and UI (optional :8891 front-end) all reach the same client. Never edits or restarts the Voice Lab / trainer.
"""
from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "voice_service",
    "name": "voice_service",
    "type": "ability",
    "status": "LIVE",
    "source": "realai.voice_service (client over realai.voice lab API / realai.voice.tts_engine)",
    "dest": "abilities/voice_service.py",
    "capabilities": ["tts", "asr", "speech", "voice", "kokoro", "xtts", "windows_sapi", "piper"],
    "read_only": False,
    "secrets_policy": "none",
}


def run(input: str = "", context: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    ctx = {**(context or {}), **kwargs}
    from realai.voice_service import get_voice_client

    c = get_voice_client()
    action = str(ctx.get("action") or ("speak" if (ctx.get("text") or input) else "health")).lower()
    if action == "health":
        return {"ok": True, "ability": "voice_service", **c.health()}
    text = str(ctx.get("text") or ctx.get("input") or input or "")
    r = c.speak(text, voice=ctx.get("voice"), backend=ctx.get("backend") or ctx.get("engine"),
                save=ctx.get("save", True) is not False)
    r.pop("audio_b64", None)
    return {"ability": "voice_service", **r}
