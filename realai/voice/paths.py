"""Local RealAI voice + GPU stack paths.

Weights:  C:\\models\\checkpoints_lora
Chat GPU: C:\\llama-vulkan (AMD Vulkan) or C:\\llama
DirectML: C:\\DirectML (training / ONNX Runtime EP)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

_MODELS = Path(os.environ.get("REALAI_MODELS_DIR") or r"C:\models\checkpoints_lora")

KOKORO_DIR = Path(os.environ.get("REALAI_KOKORO_MODEL_DIR") or (_MODELS / "Kokoro"))
FISH_DIR = Path(os.environ.get("REALAI_FISH_MODEL_DIR") or (_MODELS / "fish_speech_s1"))
XTTS_DIR = Path(os.environ.get("REALAI_XTTS_MODEL_DIR") or (_MODELS / "xtts_v2"))

VULKAN_DIR = Path(os.environ.get("REALAI_VULKAN_DIR") or r"C:\llama-vulkan")
LLAMA_DIR = Path(os.environ.get("REALAI_LLAMA_DIR") or r"C:\llama")
DIRECTML_DIR = Path(os.environ.get("REALAI_DIRECTML_DIR") or r"C:\DirectML")

VULKAN_BASE = (
    os.environ.get("REALAI_VULKAN_BASE")
    or os.environ.get("LOCAL_LLAMA_URL")
    or "http://127.0.0.1:8080"
).rstrip("/")

KOKORO_URL = (os.environ.get("REALAI_KOKORO_URL") or "http://127.0.0.1:8880").rstrip("/")
FISH_URL = (os.environ.get("REALAI_FISH_URL") or "http://127.0.0.1:8081").rstrip("/")
XTTS_URL = (os.environ.get("REALAI_XTTS_URL") or "http://127.0.0.1:8020").rstrip("/")
VOICE_LAB_URL = (os.environ.get("REALAI_VOICE_LAB_URL") or "http://127.0.0.1:8890").rstrip("/")
HIVE_URL = (os.environ.get("REALAI_HIVE_URL") or "http://127.0.0.1:8001").rstrip("/")


def models_dir() -> Path:
    return _MODELS


def kokoro_voices_dir() -> Path:
    return KOKORO_DIR / "voices"


def kokoro_checkpoint() -> Optional[Path]:
    p = KOKORO_DIR / "kokoro-v1_0.pth"
    return p if p.is_file() else None


def fish_checkpoint() -> Optional[Path]:
    for name in (
        "text2semantic-sft-large-v1.1-4k.pth",
        "text2semantic-sft-large-v1-4k.pth",
        "text2semantic-sft-medium-v1.1-4k.pth",
        "text2semantic-sft-medium-v1-4k.pth",
    ):
        p = FISH_DIR / name
        if p.is_file():
            return p
    return None


def xtts_model() -> Optional[Path]:
    p = XTTS_DIR / "model.pth"
    return p if p.is_file() else None


def xtts_speaker_wav() -> Optional[Path]:
    env = (os.environ.get("REALAI_XTTS_SPEAKER") or "").strip()
    if env and Path(env).is_file():
        return Path(env)
    # Preferred clone voice (Voice Lab / provider_config.json)
    preferred = [
        _MODELS / "voices" / "unwrenchable_clip.wav",
    _MODELS / "voices" / "travis_speaker.wav",
    _MODELS / "voices" / "myvoice (1).wav",
        _MODELS / "voices" / "unwrenchable.wav",
        _MODELS / "datasets" / "unwrenchable_voice.wav",
        XTTS_DIR / "samples" / "en_sample.wav",
        XTTS_DIR / "en_sample.wav",
    ]
    for p in preferred:
        if p.is_file():
            return p
    return None


def llama_server_exe() -> Optional[Path]:
    """Prefer AMD Vulkan build, then C:\\llama."""
    for root in (VULKAN_DIR, LLAMA_DIR):
        exe = root / "llama-server.exe"
        if exe.is_file():
            return exe
    return None


def llama_tts_exe() -> Optional[Path]:
    for root in (VULKAN_DIR, LLAMA_DIR):
        exe = root / "llama-tts.exe"
        if exe.is_file():
            return exe
    return None


def directml_runtime_dll() -> Optional[Path]:
    candidates = (
        DIRECTML_DIR / "runtime" / "x64" / "DirectML.dll",
        DIRECTML_DIR / "bin" / "x64-win" / "DirectML.dll",
    )
    for p in candidates:
        if p.is_file():
            return p
    return None


def stack_paths() -> Dict[str, Any]:
    return {
        "models_dir": str(_MODELS),
        "vulkan_dir": str(VULKAN_DIR),
        "llama_dir": str(LLAMA_DIR),
        "directml_dir": str(DIRECTML_DIR),
        "llama_server_exe": str(llama_server_exe()) if llama_server_exe() else None,
        "llama_tts_exe": str(llama_tts_exe()) if llama_tts_exe() else None,
        "directml_dll": str(directml_runtime_dll()) if directml_runtime_dll() else None,
        "urls": {
            "vulkan": VULKAN_BASE,
            "hive": HIVE_URL,
            "kokoro": KOKORO_URL,
            "fish": FISH_URL,
            "xtts": XTTS_URL,
            "voice_lab": VOICE_LAB_URL,
        },
    }


def voice_inventory() -> Dict[str, Any]:
    """Describe which local TTS weight packs and GPU servers are present."""
    kokoro_voices: List[str] = []
    vd = kokoro_voices_dir()
    if vd.is_dir():
        kokoro_voices = sorted(p.stem for p in vd.glob("*.pt"))
    return {
        "provider": "realai",
        "models_dir": str(_MODELS),
        "stack": stack_paths(),
        "kokoro": {
            "dir": str(KOKORO_DIR),
            "exists": KOKORO_DIR.is_dir(),
            "checkpoint": str(kokoro_checkpoint()) if kokoro_checkpoint() else None,
            "voices_dir": str(vd) if vd.is_dir() else None,
            "voices": kokoro_voices[:80],
            "default_voice": os.environ.get("REALAI_KOKORO_VOICE") or "af_heart",
            "url": KOKORO_URL,
        },
        "fish": {
            "dir": str(FISH_DIR),
            "exists": FISH_DIR.is_dir(),
            "checkpoint": str(fish_checkpoint()) if fish_checkpoint() else None,
            "url": FISH_URL,
        },
        "xtts": {
            "dir": str(XTTS_DIR),
            "exists": XTTS_DIR.is_dir(),
            "model": str(xtts_model()) if xtts_model() else None,
            "speaker_wav": str(xtts_speaker_wav()) if xtts_speaker_wav() else None,
            "url": XTTS_URL,
        },
        "amd": {
            "gpu_api": "vulkan",
            "cuda": False,
            "directml": directml_runtime_dll() is not None,
            "vulkan_server": str(llama_server_exe()) if llama_server_exe() else None,
        },
    }
