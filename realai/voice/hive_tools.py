"""Hive-facing voice tools for the RealAI bot.

Registerable callables: voice_speak, voice_inventory, voice_health, voice_listen.
"""

from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional

from .provider import get_voice_provider

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "voice_speak",
        "description": "Speak text aloud via local RealAI TTS (Kokoro/Fish/XTTS/Windows SAPI).",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to speak"},
                "voice": {"type": "string", "description": "Kokoro voice id, e.g. af_heart"},
                "backend": {
                    "type": "string",
                    "description": "kokoro | fish | xtts | windows_sapi | piper",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "voice_inventory",
        "description": "List local TTS weight packs under C:\\models\\checkpoints_lora.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "voice_health",
        "description": "Probe Vulkan llama-server, hive, and TTS HTTP backends.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "voice_listen",
        "description": "Transcribe base64 WAV/audio with local Whisper when available.",
        "parameters": {
            "type": "object",
            "properties": {
                "audio_b64": {"type": "string", "description": "Base64-encoded audio"},
            },
            "required": ["audio_b64"],
        },
    },
]


def voice_speak(
    text: str = "",
    voice: Optional[str] = None,
    backend: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    text = str(text or kwargs.get("input") or kwargs.get("prompt") or "").strip()
    if not text:
        text = "RealAI voice smoke check."
    result = get_voice_provider().speak(
        text,
        voice=voice,
        backend=backend,
        prepare=True,
        as_base64=True,
    )
    # Keep hive payloads compact
    b64 = result.get("audio_b64") or ""
    if len(b64) > 240:
        result["audio_b64_preview"] = b64[:120] + "…"
        result["audio_b64_len"] = len(b64)
        # Full audio still available under audio_b64 for callers that need it
    return result


def voice_inventory(**_: Any) -> Dict[str, Any]:
    return get_voice_provider().inventory()


def voice_health(**_: Any) -> Dict[str, Any]:
    return get_voice_provider().health()


def voice_listen(audio_b64: str = "", **kwargs: Any) -> Dict[str, Any]:
    demo = str(kwargs.get("demo_text") or "").strip()
    if not audio_b64 and demo:
        # TTS → ASR roundtrip for local smoke without mic/file
        spoken = get_voice_provider().speak(demo, prepare=True, as_base64=True)
        audio_b64 = str(spoken.get("audio_b64") or "")
        if not audio_b64:
            return {"ok": False, "error": "demo_tts_failed", "tts": spoken}
    try:
        audio = base64.b64decode(audio_b64) if audio_b64 else b""
    except Exception as exc:
        return {"ok": False, "error": f"bad_base64: {exc}"}
    if not audio:
        return {
            "ok": False,
            "error": "audio_required",
            "hint": "Pass audio_b64 or demo_text for TTS→ASR roundtrip",
        }
    # Prefer ability.audio_transcription (vosk) when provider listen is stubby
    try:
        from abilities.audio_transcription import run as asr_run

        out = asr_run(context={"audio_b64": audio_b64})
        if out.get("ok") and out.get("text"):
            return {"ok": True, "text": out.get("text"), "backend": out.get("backend"), "ability": "audio_transcription"}
    except Exception:
        pass
    return get_voice_provider().listen(audio)


DISPATCH = {
    "voice_speak": voice_speak,
    "voice_inventory": voice_inventory,
    "voice_health": voice_health,
    "voice_listen": voice_listen,
}


def execute(name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    fn = DISPATCH.get(name)
    if not fn:
        return {"ok": False, "error": f"unknown_voice_tool: {name}"}
    return fn(**(arguments or {}))


def tool_catalog() -> List[Dict[str, Any]]:
    return list(TOOLS)
