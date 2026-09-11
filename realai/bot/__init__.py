"""RealAI Bot package — local-only default persona and prompt injection."""

from __future__ import annotations

from realai.bot.boot import (
    DEFAULT_REALAI_PROMPT,
    inject_system,
    load_prompt,
    maybe_voice_route,
    prepare_bot_speech,
    register_default_bot,
    resolve_local_model,
    voice_enabled,
)

__all__ = [
    "DEFAULT_REALAI_PROMPT",
    "inject_system",
    "load_prompt",
    "maybe_voice_route",
    "prepare_bot_speech",
    "register_default_bot",
    "resolve_local_model",
    "voice_enabled",
]
