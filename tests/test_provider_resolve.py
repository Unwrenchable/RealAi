"""Bearer + no X-Provider defaults to self-host realai."""

from __future__ import annotations

from realai.provider_resolve import (
    default_selfhost_provider,
    detect_provider_from_key,
    realai_constructor_provider,
    resolve_request_provider,
)

PREFIXES = {
    "sk-ant-": "anthropic",
    "sk-or-v1-": "openrouter",
    "sk-proj-": "openai",
    "sk-": "openai",
    "xai-": "grok",
    "AIza": "gemini",
    "pplx-": "perplexity",
}


def test_bearer_no_header_defaults_to_realai():
    assert resolve_request_provider(None, "local-internal-key", PREFIXES) == "realai"
    assert resolve_request_provider("", "hive-token-abc", PREFIXES) == "realai"
    assert resolve_request_provider("auto", "not-a-cloud-prefix", PREFIXES) == "realai"


def test_local_and_realai_are_the_same_selfhost_path():
    assert resolve_request_provider("local", None, PREFIXES) == "realai"
    assert resolve_request_provider("realai", None, PREFIXES) == "realai"
    assert resolve_request_provider("LOCAL", "sk-proj-ignored", PREFIXES) == "realai"
    assert realai_constructor_provider("realai") == "local"
    assert realai_constructor_provider("local") == "local"


def test_explicit_cloud_header_wins_over_unknown_key():
    assert resolve_request_provider("openai", "local-internal-key", PREFIXES) == "openai"
    assert resolve_request_provider("anthropic", "xai-should-not-matter", PREFIXES) == "anthropic"
    assert realai_constructor_provider("openai") == "openai"


def test_known_prefix_without_header_stays_auto_detect():
    assert resolve_request_provider(None, "sk-proj-abc", PREFIXES) is None
    assert resolve_request_provider("auto", "sk-ant-abc", PREFIXES) is None
    assert detect_provider_from_key("sk-or-v1-abc", PREFIXES) == "openrouter"


def test_no_bearer_does_not_invent_provider():
    assert resolve_request_provider(None, None, PREFIXES) is None
    assert resolve_request_provider("auto", "", PREFIXES) is None


def test_realai_provider_env_override(monkeypatch):
    monkeypatch.setenv("REALAI_PROVIDER", "realai")
    assert default_selfhost_provider() == "realai"
    monkeypatch.setenv("REALAI_PROVIDER", "custom-hive")
    assert default_selfhost_provider() == "custom-hive"
    assert resolve_request_provider(None, "internal", PREFIXES) == "custom-hive"
    assert resolve_request_provider("local", None, PREFIXES) == "custom-hive"
    assert realai_constructor_provider("custom-hive") == "local"
    monkeypatch.setenv("REALAI_PROVIDER", "  ")
    assert default_selfhost_provider() == "realai"
