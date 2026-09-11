"""RealAI Voice Provider — provider-level speak / listen / inventory.

Local-only. Uses checkpoints under C:\\models\\checkpoints_lora and AMD
Vulkan / DirectML stack paths. No cloud TTS (no xAI / Grok Voice).
"""

from __future__ import annotations

import base64
import os
from typing import Any, Dict, Optional

from .paths import voice_inventory
from .persona import DEFAULT_PERSONA, prepare_speech_text
from .servers import preferred_tts_http, stack_health
from .tts_engine import TTSEngine, get_tts_engine
from pathlib import Path

PROVIDER_ID = "realai-voice"
PROVIDER_NAME = "RealAI Voice"


class VoiceProvider:
    """Provider-level façade used by hive bot, abilities, and Voice Lab."""

    id = PROVIDER_ID
    name = PROVIDER_NAME

    def __init__(self, engine: Optional[TTSEngine] = None) -> None:
        self._engine = engine or get_tts_engine()
        self.persona = DEFAULT_PERSONA

    def health(self, *, deep: bool = False) -> Dict[str, Any]:
        # Quick by default — full TTS HTTP probes only when deep=True.
        stack = stack_health(quick=not deep)
        inv = voice_inventory()
        preferred = preferred_tts_http() if deep else None
        return {
            "ok": True,
            "provider": PROVIDER_ID,
            "preferred_http_tts": preferred,
            "default_backend": os.environ.get("REALAI_TTS_BACKEND") or "xtts",
            "windows_sapi": os.name == "nt",
            "models_present": {
                "kokoro": bool(inv.get("kokoro", {}).get("checkpoint")),
                "fish": bool(inv.get("fish", {}).get("checkpoint")),
                "xtts": bool(inv.get("xtts", {}).get("model")),
            },
            "xtts_speaker": os.environ.get("REALAI_XTTS_SPEAKER")
            or (inv.get("xtts") or {}).get("speaker_wav"),
            "stack": stack,
        }

    def inventory(self) -> Dict[str, Any]:
        return voice_inventory()

    def prepare(self, text: str) -> str:
        return prepare_speech_text(text, self.persona)

    def speak(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        backend: Optional[str] = None,
        prepare: bool = True,
        as_base64: bool = False,
    ) -> Dict[str, Any]:
        """Synthesize speech. Returns WAV bytes (or base64) + backend metadata."""
        voice_id = str(voice).strip().lower() if voice else ""
        if voice_id in ("laura", "unwrenchable", "clone"):
            # Product voice id -> XTTS speaker clip (never treat as Kokoro id)
            speaker = (
                os.environ.get("REALAI_XTTS_SPEAKER")
                or r"C:\models\checkpoints_lora\voices\unwrenchable_clip.wav"
            )
            if Path(speaker).is_file():
                os.environ["REALAI_XTTS_SPEAKER"] = speaker
            if not backend:
                backend = "xtts"
        elif voice:
            os.environ["REALAI_KOKORO_VOICE"] = str(voice).strip()
        if backend:
            # Rebuild engine with preferred backend first
            os.environ["REALAI_TTS_BACKEND"] = str(backend).strip().lower()
            self._engine = get_tts_engine()

        spoken = self.prepare(text) if prepare else (text or "").strip()
        if not spoken:
            return {
                "ok": False,
                "error": "empty_speech_text",
                "provider": PROVIDER_ID,
                "spoken_text": "",
            }

        audio = self._engine.synthesize(spoken, prepare=False)
        backend_used = self._engine.last_backend
        err = self._engine.last_error
        ok = bool(audio) and len(audio) > 64 and (audio[:4] == b"RIFF" or len(audio) > 512)
        wanted = str(backend or "").strip().lower()
        if wanted in ("xtts", "coqui") and backend_used != "xtts":
            ok = False
            err = err or f"xtts_unavailable_got_{backend_used or 'none'}"
        out: Dict[str, Any] = {
            "ok": ok,
            "provider": PROVIDER_ID,
            "spoken_text": spoken,
            "backend": backend_used,
            "format": "wav",
            "bytes": len(audio or b""),
            "voice": (
                "laura"
                if voice_id in ("laura", "unwrenchable", "clone") or backend_used == "xtts"
                else (os.environ.get("REALAI_KOKORO_VOICE") or "af_heart")
            ),
        }
        if err and not ok:
            out["error"] = err
        if as_base64:
            out["audio_b64"] = base64.b64encode(audio or b"").decode("ascii")
        else:
            out["audio"] = audio
        return out

    def listen(self, audio_bytes: bytes, **kwargs: Any) -> Dict[str, Any]:
        """ASR via Whisper when available."""
        try:
            from .asr_whisper import WhisperASR

            asr = WhisperASR()
            result = asr.transcribe(audio_bytes, **kwargs)
            text = str((result or {}).get("text") or "").strip()
            return {
                "ok": bool(text) and "unavailable" not in text.lower(),
                "provider": PROVIDER_ID,
                "backend": asr.name,
                "text": text,
            }
        except Exception as exc:
            return {"ok": False, "provider": PROVIDER_ID, "error": str(exc), "text": ""}

    def hive_speak(self, text: str, intent: str = "chat") -> Dict[str, Any]:
        """Bot-facing speak path: respect routing intents, fail soft."""
        try:
            from realai.orchestration.tts_routing import should_speak

            if not should_speak(intent, text or ""):
                return {
                    "ok": True,
                    "speak": False,
                    "provider": PROVIDER_ID,
                    "spoken_text": "",
                    "reason": "text_only_intent",
                }
        except Exception:
            pass
        result = self.speak(text, prepare=True, as_base64=True)
        result["speak"] = bool(result.get("ok"))
        result["intent"] = intent
        return result


_PROVIDER: Optional[VoiceProvider] = None


def get_voice_provider() -> VoiceProvider:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = VoiceProvider()
    return _PROVIDER
