"""ASR backend protocol."""

from typing import Any, Dict, Protocol


class ASRBackend(Protocol):
    name: str

    def transcribe(self, audio_bytes: bytes, **kwargs: Any) -> Dict[str, Any]:
        ...

