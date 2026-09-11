"""TTS ability — RealAI Voice provider (Kokoro/Fish/XTTS/Windows SAPI/Piper)."""

from __future__ import annotations

import base64
from typing import Any

ABILITY = {
    "id": "audio_speech",
    "name": "audio_speech",
    "type": "ability",
    "status": "LIVE",
    "source": "realai.voice.provider + realai.voice.tts_engine",
    "dest": "abilities/audio_speech.py",
    "capabilities": ["tts", "speech", "kokoro", "fish", "xtts", "windows_sapi", "piper"],
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

    voice = ctx.get("voice")
    backend = ctx.get("backend") or ctx.get("engine")

    try:
        from realai.voice.provider import get_voice_provider

        result = get_voice_provider().speak(
            text,
            voice=str(voice) if voice else None,
            backend=str(backend) if backend else None,
            prepare=True,
            as_base64=True,
        )
        b64 = result.get("audio_b64") or ""
        return {
            "ok": bool(result.get("ok")),
            "ability": "audio_speech",
            "backend": result.get("backend"),
            "live_model": bool(result.get("ok")),
            "format": "wav",
            "bytes": result.get("bytes") or 0,
            "voice": result.get("voice"),
            "spoken_text": result.get("spoken_text"),
            "audio_b64": b64[:200] + "…" if b64 and len(b64) > 200 else b64,
            "audio_b64_full": b64 if ctx.get("full_audio") else None,
            "text_echo": text[:500],
            "live_path": "POST /v1/audio/speech (Voice Lab :8890 or Hive)",
            "error": result.get("error"),
            "provider": "realai-voice",
        }
    except Exception as exc:
        # Last-resort stub so hive tools never hard-crash
        try:
            from realai.lambda_embeddings_audio import create_speech_response

            stub = create_speech_response({"input": text, "voice": voice})
            return {
                "ok": True,
                "ability": "audio_speech",
                "backend": "lambda_stub",
                "live_model": False,
                "result": stub,
                "live_path": "POST /v1/audio/speech",
                "note": f"Voice provider failed: {exc}",
                "error": str(exc),
            }
        except Exception as stub_exc:
            return {
                "ok": False,
                "ability": "audio_speech",
                "error": str(exc),
                "stub_error": str(stub_exc),
            }
