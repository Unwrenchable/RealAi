"""Bearer + no X-Provider defaults to self-host realai."""

from __future__ import annotations

from realai.provider_resolve import (
    default_selfhost_provider,
    detect_provider_from_key,
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


def test_explicit_cloud_header_wins_over_unknown_key():
    assert resolve_request_provider("openai", "local-internal-key", PREFIXES) == "openai"
    assert resolve_request_provider("anthropic", "xai-should-not-matter", PREFIXES) == "anthropic"


def test_known_prefix_without_header_stays_auto_detect():
    assert resolve_request_provider(None, "sk-proj-abc", PREFIXES) is None
    assert resolve_request_provider(None, "sk-ant-abc", PREFIXES) is None
    assert detect_provider_from_key("sk-or-v1-abc", PREFIXES) == "openrouter"


def test_no_bearer_does_not_invent_provider():
    assert resolve_request_provider(None, None, PREFIXES) is None
    assert resolve_request_provider(None, "", PREFIXES) is None


def test_realai_provider_env_override(monkeypatch):
    monkeypatch.setenv("REALAI_PROVIDER", "realai")
    assert default_selfhost_provider() == "realai"
    monkeypatch.setenv("REALAI_PROVIDER", "custom-hive")
    assert default_selfhost_provider() == "custom-hive"
    assert resolve_request_provider(None, "internal", PREFIXES) == "custom-hive"
    monkeypatch.setenv("REALAI_PROVIDER", "  ")
    assert default_selfhost_provider() == "realai"
