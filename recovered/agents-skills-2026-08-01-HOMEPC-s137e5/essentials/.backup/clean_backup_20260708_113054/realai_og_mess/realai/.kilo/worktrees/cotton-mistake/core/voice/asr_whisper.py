"""Whisper-compatible ASR backend with graceful fallback."""

from typing import Any, Dict


class WhisperASR:
    name = "whisper-asr"

    def __init__(self, model_path: str = "models/whisper-small"):
        self.model_path = model_path
        self._model = None
        try:
            from faster_whisper import WhisperModel  # type: ignore
            self._model = WhisperModel(model_path)
        except Exception:
            self._model = None

    def transcribe(self, audio_bytes: bytes, **kwargs: Any) -> Dict[str, Any]:
        if self._model is not None:
            try:
                segments, _info = self._model.transcribe(audio_bytes)
                text = " ".join(segment.text for segment in segments).strip()
                return {"text": text}
            except Exception:
                pass
        return {"text": "Transcription unavailable in local runtime fallback."}

