"""Audio routes."""

import io

from fastapi import APIRouter, UploadFile
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from apps.api.state import voice_registry
from core.api.schemas.audio import TTSRequest

router = APIRouter()
MAX_AUDIO_BYTES = 960_000  # ~30 seconds @16kHz mono 16-bit PCM


@router.post("/v1/audio/transcriptions")
def transcribe_audio(file: UploadFile):
    audio_bytes = file.file.read()
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio exceeds 30 second limit")
    backend = voice_registry.get_asr("whisper-asr")
    return backend.transcribe(audio_bytes)


@router.post("/v1/audio/speech")
def synthesize_audio(req: TTSRequest):
    backend = voice_registry.get_tts(req.voice)
    audio_bytes = backend.synthesize(req.text)
    return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/wav")
