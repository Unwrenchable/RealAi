"""TTS backend protocol."""

from typing import Protocol


class TTSBackend(Protocol):
    name: str

    def synthesize(self, text: str) -> bytes:
        ...

