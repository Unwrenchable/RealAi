"""Focused RealAI Bot local-only tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("REALAI_BOT_LOCAL_ONLY", "1")


def test_default_system_prompt_is_realai():
    from realai.identity import PERSONA_SWITCHER

    # Clear active persona so fallback is used.
    PERSONA_SWITCHER.active = None
    prompt = PERSONA_SWITCHER.get_active_system_prompt()
    assert "You are RealAI" in prompt
    assert "helpful AI assistant" not in prompt


def test_inject_system_once():
    from realai.bot.boot import inject_system

    msgs = [{"role": "user", "content": "hi"}]
    out = inject_system(msgs)
    assert out[0]["role"] == "system"
    assert "You are RealAI" in out[0]["content"]
    assert len([m for m in out if m.get("role") == "system"]) == 1

    again = inject_system(out)
    assert len([m for m in again if m.get("role") == "system"]) == 1
    assert again[0]["content"] == out[0]["content"]


def test_register_default_bot_idempotent():
    from realai.bot.boot import register_default_bot
    from realai.identity import PERSONA_SWITCHER

    first = register_default_bot()
    second = register_default_bot()
    assert first.get("ok") is True
    assert second.get("ok") is True
    assert PERSONA_SWITCHER.active is not None
    assert PERSONA_SWITCHER.active.name == "RealAI Bot"


def test_select_realai_bot_provider_local_only():
    from realai.router import select_realai_bot_provider

    provider = select_realai_bot_provider()
    assert provider in ("local", "realai")


def test_coerce_blocks_grok_models():
    from realai.bot.boot import coerce_local_model

    assert coerce_local_model("grok-4") == coerce_local_model(None) or coerce_local_model("grok-4").startswith("realai")
    assert "grok" not in coerce_local_model("gpt-4o").lower()
    assert coerce_local_model("realai-default-coder") == "realai-default-coder"


def test_local_only_detect_provider():
    from realai import _detect_provider

    os.environ["REALAI_BOT_LOCAL_ONLY"] = "1"
    assert _detect_provider("xai-test-key", None) == "local"
    assert _detect_provider(None, None) == "local"


if __name__ == "__main__":
    test_default_system_prompt_is_realai()
    test_inject_system_once()
    test_register_default_bot_idempotent()
    test_select_realai_bot_provider_local_only()
    test_coerce_blocks_grok_models()
    test_local_only_detect_provider()
    print("OK realai bot tests")
