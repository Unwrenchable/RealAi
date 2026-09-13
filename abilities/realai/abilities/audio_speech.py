"""TTS ability — prefers core.voice Piper, falls back to orchestrator stub."""

from __future__ import annotations

import base64
from typing import Any

ABILITY = {
    "id": "audio_speech",
    "name": "audio_speech",
    "type": "ability",
    "status": "PARTIAL",
    "source": "core.voice.tts_piper + realai.lambda_embeddings_audio",
    "dest": "abilities/audio_speech.py",
    "capabilities": ["tts", "speech", "piper"],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    text = str(ctx.get("text") or ctx.get("input") or input or "").strip()
    if not text:
        return {"ok": False, "error": "text_required", "ability": "audio_speech"}

    backend = "stub"
    audio_b64 = None
    audio_len = 0
    try:
        from core.voice.tts_piper import PiperTTS

        tts = PiperTTS()
        wav = tts.synthesize(text)
        audio_len = len(wav or b"")
        audio_b64 = base64.b64encode(wav or b"").decode("ascii") if wav else None
        # silent wav is 44 bytes — treat longer as likely real piper output
        backend = "piper" if audio_len > 44 else "piper_fallback_silent"
    except Exception:
        from realai.lambda_embeddings_audio import create_speech_response

        stub = create_speech_response({"input": text, "voice": ctx.get("voice")})
        return {
            "ok": True,
            "ability": "audio_speech",
            "backend": "lambda_stub",
            "live_model": False,
            "result": stub,
            "live_path": "POST /v1/audio/speech",
            "note": "Install piper CLI + voice model for live TTS",
        }

    return {
        "ok": True,
        "ability": "audio_speech",
        "backend": backend,
        "live_model": backend == "piper",
        "format": "wav",
        "bytes": audio_len,
        "audio_b64": audio_b64[:200] + "…" if audio_b64 and len(audio_b64) > 200 else audio_b64,
        "text_echo": text[:500],
        "live_path": "POST /v1/audio/speech",
        "note": None
        if backend == "piper"
        else "Piper binary/model not available — returned silent WAV fallback; endpoint remains callable",
    }
