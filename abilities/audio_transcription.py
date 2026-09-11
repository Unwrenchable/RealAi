"""ASR ability — local Vosk first, then Whisper, then stub (still callable)."""

from __future__ import annotations

import base64
import json
import wave
from pathlib import Path
from typing import Any, Optional

ABILITY = {
    "id": "audio_transcription",
    "name": "audio_transcription",
    "type": "ability",
    "status": "LIVE",
    "source": "vosk + optional whisper",
    "dest": "abilities/audio_transcription.py",
    "capabilities": ["asr", "transcription", "vosk", "whisper"],
    "secrets_policy": "none",
}

_VOSK_CANDIDATES = [
    Path(r"C:\models\vosk\vosk-model-small-en-us-0.15"),
    Path(r"C:\models\vosk\vosk-model-en-us-0.22"),
    Path(__file__).resolve().parents[1] / "models" / "vosk" / "vosk-model-small-en-us-0.15",
]


def _resolve_vosk_model() -> Optional[Path]:
    import os

    env = os.environ.get("VOSK_MODEL") or os.environ.get("VOSK_MODEL_PATH")
    if env and Path(env).is_dir():
        return Path(env)
    for p in _VOSK_CANDIDATES:
        if p.is_dir() and (p / "am").is_dir():
            return p
    return None


def _pcm_from_wav(audio_bytes: bytes) -> tuple[bytes, int]:
    """Return mono PCM16 + sample rate from WAV bytes (or raw if not WAV)."""
    if len(audio_bytes) >= 12 and audio_bytes[:4] == b"RIFF":
        with wave.open(__import__("io").BytesIO(audio_bytes), "rb") as wf:
            rate = wf.getframerate()
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            frames = wf.readframes(wf.getnframes())
        if sampwidth != 2:
            # best-effort: leave as-is; vosk wants 16-bit
            pass
        if channels > 1:
            # downmix interleaved int16
            import array

            arr = array.array("h")
            arr.frombytes(frames)
            mono = array.array("h", (arr[i] for i in range(0, len(arr), channels)))
            frames = mono.tobytes()
        return frames, rate
    return audio_bytes, 16000


def _transcribe_vosk(audio_bytes: bytes) -> dict[str, Any]:
    import vosk

    model_path = _resolve_vosk_model()
    if model_path is None:
        return {"ok": False, "error": "vosk_model_missing"}

    pcm, rate = _pcm_from_wav(audio_bytes)
    if rate not in (8000, 16000, 32000, 44100, 48000):
        rate = 16000
    model = vosk.Model(str(model_path))
    rec = vosk.KaldiRecognizer(model, rate)
    rec.SetWords(True)
    # feed in chunks
    chunk = 4000
    for i in range(0, max(len(pcm), 1), chunk):
        rec.AcceptWaveform(pcm[i : i + chunk])
    final = json.loads(rec.FinalResult() or "{}")
    text = str(final.get("text") or "").strip()
    return {
        "ok": True,
        "backend": "vosk",
        "live_model": True,
        "text": text,
        "model_path": str(model_path),
        "sample_rate": rate,
        "raw": final,
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

    # If caller only sent text path with no audio, synthesize a TTS sample then ASR it
    # so the ability is demonstrably live end-to-end without cloud.
    if not audio_bytes and str(ctx.get("demo_text") or "").strip():
        try:
            from abilities.audio_speech import run as tts_run

            tts = tts_run(input=str(ctx.get("demo_text")), context={"text": str(ctx.get("demo_text")), "full_audio": True})
            b64 = tts.get("audio_b64_full") or ""
            if b64:
                audio_bytes = base64.b64decode(b64)
        except Exception:
            pass

    if not audio_bytes:
        return {
            "ok": False,
            "ability": "audio_transcription",
            "error": "audio_required",
            "hint": "Pass audio_b64, file path, or demo_text for TTS→ASR roundtrip",
            "vosk_model": str(_resolve_vosk_model() or ""),
        }

    # 1) Vosk (local)
    try:
        vosk_out = _transcribe_vosk(audio_bytes)
        if vosk_out.get("ok"):
            return {
                "ok": True,
                "ability": "audio_transcription",
                "backend": "vosk",
                "live_model": True,
                "text": vosk_out.get("text") or "",
                "live_path": "POST /v1/audio/transcriptions + ability.audio_transcription (vosk local)",
                "model_path": vosk_out.get("model_path"),
                "local": True,
            }
    except Exception as e:
        vosk_err = str(e)
    else:
        vosk_err = vosk_out.get("error") if isinstance(vosk_out, dict) else None

    # 2) Whisper if installed
    try:
        from core.voice.asr_whisper import WhisperASR

        asr = WhisperASR()
        result = asr.transcribe(audio_bytes)
        text = str((result or {}).get("text") or "")
        live = getattr(asr, "_model", None) is not None and text and "unavailable" not in text.lower()
        if live:
            return {
                "ok": True,
                "ability": "audio_transcription",
                "backend": "whisper",
                "live_model": True,
                "text": text,
                "live_path": "POST /v1/audio/transcriptions",
                "local": True,
            }
    except Exception as e:
        whisper_err = str(e)
    else:
        whisper_err = None

    return {
        "ok": False,
        "ability": "audio_transcription",
        "backend": "unavailable",
        "live_model": False,
        "text": "",
        "error": "asr_backends_failed",
        "vosk_error": vosk_err,
        "whisper_error": whisper_err,
        "vosk_model": str(_resolve_vosk_model() or ""),
        "local": True,
    }
