"""RealAI voice provider registration for hive / abilities."""

from __future__ import annotations

from typing import Any, Dict, Optional

from realai.voice.provider import VoiceProvider, get_voice_provider

PROVIDER = {
    "id": "realai-voice",
    "name": "RealAI Voice",
    "type": "voice",
    "local": True,
    "cloud": False,
    "models_dir": r"C:\models\checkpoints_lora",
    "backends": ["kokoro", "fish", "xtts", "windows_sapi", "piper"],
    "gpu": {
        "vulkan_dir": r"C:\llama-vulkan",
        "llama_dir": r"C:\llama",
        "directml_dir": r"C:\DirectML",
    },
}


def get_provider() -> VoiceProvider:
    return get_voice_provider()


def speak(text: str, **kwargs: Any) -> Dict[str, Any]:
    return get_provider().speak(text, as_base64=True, **kwargs)


def health() -> Dict[str, Any]:
    return get_provider().health()


def inventory() -> Dict[str, Any]:
    return get_provider().inventory()


def info() -> Dict[str, Any]:
    return dict(PROVIDER)
