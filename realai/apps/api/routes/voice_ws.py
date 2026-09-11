"""Streaming voice WebSocket endpoint."""

from fastapi import APIRouter, WebSocket

from apps.api.state import inference_registry, voice_registry

router = APIRouter()


@router.websocket("/v1/voice")
async def voice_stream(ws: WebSocket):
    await ws.accept()
    asr_backend = voice_registry.get_asr("whisper-asr")
    tts_backend = voice_registry.get_tts("piper-tts")
    chat_backend = inference_registry.get_chat("realai-default")

    while True:
        audio_chunk = await ws.receive_bytes()
        text = asr_backend.transcribe(audio_chunk).get("text", "")
        response = chat_backend.generate([{"role": "user", "content": text}])
        assistant = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        audio_out = tts_backend.synthesize(assistant)
        await ws.send_bytes(audio_out)

