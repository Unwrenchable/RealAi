"""Audio API schemas."""

from pydantic import BaseModel


class TTSRequest(BaseModel):
    text: str
    voice: str = "piper-tts"

