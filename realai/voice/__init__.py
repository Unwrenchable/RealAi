"""RealAI Voice — local TTS/ASR provider for the hive bot + Voice Lab.

Weights: C:\\models\\checkpoints_lora (Kokoro, Fish Speech, XTTS)
GPU chat: C:\\llama-vulkan (AMD Vulkan) or C:\\llama
DirectML: C:\\DirectML
"""

from .asr_whisper import WhisperASR
from .hive_tools import execute as execute_voice_tool
from .hive_tools import tool_catalog as voice_tool_catalog
from .paths import stack_paths, voice_inventory
from .persona import DEFAULT_PERSONA, prepare_speech_text
from .provider import VoiceProvider, get_voice_provider
from .registry import VoiceRegistry
from .servers import stack_health
from .tts_engine import TTSEngine, get_tts_engine
from .tts_piper import PiperTTS

__all__ = [
    "DEFAULT_PERSONA",
    "PiperTTS",
    "TTSEngine",
    "VoiceProvider",
    "VoiceRegistry",
    "WhisperASR",
    "execute_voice_tool",
    "get_tts_engine",
    "get_voice_provider",
    "prepare_speech_text",
    "stack_health",
    "stack_paths",
    "voice_inventory",
    "voice_tool_catalog",
]
