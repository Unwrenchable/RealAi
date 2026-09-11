"""RealAI Voice Engine.

Picks a TTS backend (Kokoro, Fish Speech, XTTS, Piper) and turns
speech-ready text into WAV bytes. Import is side-effect free.
Does not start servers, Craft, or llama.
"""

from __future__ import annotations

import os
from typing import Iterable, Optional

from .tts_base import TTSBackend
from .tts_piper import PiperTTS
from .persona import DEFAULT_PERSONA, prepare_speech_text

BACKEND_ORDER = ("kokoro", "fish", "xtts", "piper")


class KokoroTTS:
    """Kokoro HTTP backend. Optional; falls back if unreachable."""

    name = "kokoro"

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (
            base_url
            or os.environ.get("REALAI_KOKORO_URL")
            or "http://127.0.0.1:8880"
        ).rstrip("/")

    def synthesize(self, text: str) -> bytes:
        import json
        import urllib.request

        payload = json.dumps(
            {
                "model": "kokoro",
                "input": text,
                "voice": os.environ.get("REALAI_KOKORO_VOICE", "af_heart"),
                "response_format": "wav",
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/v1/audio/speech",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()


class FishSpeechTTS:
    name = "fish"

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (
            base_url
            or os.environ.get("REALAI_FISH_URL")
            or "http://127.0.0.1:8081"
        ).rstrip("/")

    def synthesize(self, text: str) -> bytes:
        import json
        import urllib.request

        payload = json.dumps({"text": text, "format": "wav"}).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/v1/tts",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()


class XTTSBackend:
    name = "xtts"

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (
            base_url
            or os.environ.get("REALAI_XTTS_URL")
            or "http://127.0.0.1:8020"
        ).rstrip("/")

    def synthesize(self, text: str) -> bytes:
        import json
        import urllib.request

        payload = json.dumps(
            {
                "text": text,
                "speaker_wav": os.environ.get("REALAI_XTTS_SPEAKER", ""),
                "language": os.environ.get("REALAI_XTTS_LANG", "en"),
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/tts",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()


class TTSEngine:
    """Speech-ready TTS with ordered backend fallback."""

    def __init__(self, backends: Optional[Iterable[TTSBackend]] = None) -> None:
        preferred = (os.environ.get("REALAI_TTS_BACKEND") or "kokoro").strip().lower()
        built = {
            "kokoro": KokoroTTS(),
            "fish": FishSpeechTTS(),
            "xtts": XTTSBackend(),
            "piper": PiperTTS(),
        }
        if backends is not None:
            self._backends = list(backends)
        else:
            order = [preferred] + [name for name in BACKEND_ORDER if name != preferred]
            self._backends = [built[name] for name in order if name in built]
        self.persona = DEFAULT_PERSONA

    def prepare(self, text: str) -> str:
        return prepare_speech_text(text, self.persona)

    def synthesize(self, text: str, prepare: bool = True) -> bytes:
        spoken = self.prepare(text) if prepare else (text or "").strip()
        if not spoken:
            from .tts_piper import _silent_wav

            return _silent_wav()
        last_error = None
        for backend in self._backends:
            try:
                audio = backend.synthesize(spoken)
                if audio:
                    return audio
            except Exception as exc:
                last_error = exc
                continue
        from .tts_piper import _silent_wav

        _ = last_error
        return _silent_wav()

    def speak(self, text: str) -> bytes:
        """Alias for synthesize with speech prep on."""
        return self.synthesize(text, prepare=True)


def get_tts_engine() -> TTSEngine:
    return TTSEngine()
