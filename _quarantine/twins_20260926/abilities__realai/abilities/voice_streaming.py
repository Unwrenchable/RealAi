"""Voice interaction — one-shot ASR→chat→TTS via core.voice; WS lives under apps/api."""

from __future__ import annotations

import base64
from typing import Any

ABILITY = {
    "id": "voice_streaming",
    "name": "voice_streaming",
    "type": "ability",
    "status": "PARTIAL",
    "source": "core.voice + apps.api.routes.voice_ws",
    "dest": "abilities/voice_streaming.py",
    "capabilities": ["voice", "asr", "tts", "streaming_ws"],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """One-shot voice turn. Full duplex WS: apps/api/routes/voice_ws.py → /v1/voice."""
    ctx = dict(context or {})
    ctx.update(kwargs)
    mode = str(ctx.get("mode") or "status").lower()

    asr_ok = False
    tts_ok = False
    try:
        from core.voice.asr_whisper import WhisperASR

        asr_ok = WhisperASR()._model is not None
    except Exception:
        asr_ok = False
    try:
        from core.voice.tts_piper import PiperTTS

        # probe synthesize
        tts_ok = len(PiperTTS().synthesize("ok") or b"") > 44
    except Exception:
        tts_ok = False

    if mode in {"status", "info", ""}:
        return {
            "ok": True,
            "ability": "voice_streaming",
            "mode": "status",
            "asr_model_loaded": asr_ok,
            "tts_live": tts_ok,
            "websocket": {
                "path": "apps/api/routes/voice_ws.py",
                "route": "WS /v1/voice",
                "note": "Served by FastAPI apps.api — not the stdlib Hive :8001",
            },
            "oneshot": "Pass mode=turn with text=… (or audio_b64) for ASR→optional chat→TTS",
            "partial_reason": "WS stack exists; Hive exposes one-shot turn; full streaming needs apps.api up",
        }

    # one-shot turn
    text_in = str(ctx.get("text") or input or "").strip()
    if not text_in and ctx.get("audio_b64"):
        from abilities.audio_transcription import run as asr_run

        asr = asr_run(context={"audio_b64": ctx.get("audio_b64")})
        text_in = str(asr.get("text") or "")

    if not text_in:
        return {"ok": False, "error": "text_or_audio_required", "ability": "voice_streaming"}

    reply = text_in
    chat_used = False
    if ctx.get("chat", True):
        try:
            import json
            import urllib.request

            body = json.dumps(
                {
                    "model": "realai-default-coder",
                    "messages": [{"role": "user", "content": text_in}],
                    "max_tokens": int(ctx.get("max_tokens") or 128),
                }
            ).encode()
            req = urllib.request.Request(
                "http://127.0.0.1:8001/v1/chat/completions",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
            reply = (
                ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
                or reply
            )
            chat_used = True
        except Exception as e:
            reply = f"(chat unavailable: {e}) echo: {text_in}"

    from abilities.audio_speech import run as tts_run

    tts = tts_run(input=str(reply)[:500], context={"text": str(reply)[:500]})
    return {
        "ok": True,
        "ability": "voice_streaming",
        "mode": "turn",
        "input_text": text_in,
        "reply": reply,
        "chat_used": chat_used,
        "tts": tts,
        "websocket_hint": "WS /v1/voice via apps.api for streaming chunks",
    }
