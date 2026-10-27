"""Compatibility shim -> realai.voice.tts_engine (canonical voice engine, decision 4).

This agent_tools copy was the oldest phase (HTTP-only Kokoro/Fish/XTTS + Piper, 157 lines) and was not importable
(its relative imports .tts_base / .tts_piper do not exist under agent_tools). Every def it had exists in the canonical
engine, which adds Kokoro/XTTS local synthesis, Windows SAPI, _is_real_wav/MIN_REAL_WAV, provider_config and
speaker-clip helpers. For agents/hive/CLI/UI prefer realai.voice_service (shared client).
"""
from realai.voice.tts_engine import *  # noqa: F401,F403
from realai.voice.tts_engine import (  # noqa: F401
    BACKEND_ORDER, MIN_REAL_WAV, FishSpeechTTS, KokoroTTS, TTSEngine, WindowsSAPI, XTTSBackend, _is_real_wav,
    get_tts_engine,
)
