"""ASR ability — prefers core.voice Whisper, falls back to orchestrator stub."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

ABILITY = {
    "id": "audio_transcription",
    "name": "audio_transcription",
    "type": "ability",
    "status": "PARTIAL",
    "source": "core.voice.asr_whisper + realai.lambda_embeddings_audio",
    "dest": "abilities/audio_transcription.py",
    "capabilities": ["asr", "transcription", "whisper"],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    audio_bytes = b""
    if isinstance(ctx.get("audio_bytes"), (bytes, bytearray)):
        audio_bytes = bytes(ctx["audio_bytes"])
    elif ctx.get("audio_b64"):
        try:
            audio_bytes = base64.b64decode(str(ctx.get("audio_b64")))
        except Exception:
            audio_bytes = b""
    elif ctx.get("file") or ctx.get("path") or input:
        path = Path(str(ctx.get("file") or ctx.get("path") or input))
        if path.is_file():
            audio_bytes = path.read_bytes()

    backend = "stub"
    text = ""
    try:
        from core.voice.asr_whisper import WhisperASR

        asr = WhisperASR()
        result = asr.transcribe(audio_bytes or b"")
        text = str((result or {}).get("text") or "")
        backend = "whisper" if getattr(asr, "_model", None) is not None else "whisper_fallback"
    except Exception as e:
        from realai.lambda_embeddings_audio import create_transcription_response

        stub = create_transcription_response({"file": ctx.get("file") or input, "language": ctx.get("language")})
        text = stub.get("text") or str(e)
        backend = "lambda_stub"

    live = backend == "whisper" and text and "unavailable" not in text.lower()
    return {
        "ok": True,
        "ability": "audio_transcription",
        "backend": backend,
        "live_model": live,
        "text": text,
        "live_path": "POST /v1/audio/transcriptions",
        "note": None
        if live
        else "Whisper model not loaded — install faster-whisper for full ASR; endpoint remains callable",
    }
