"""Cloud UI vs local default_llm: fallback, messaging, Vulkan loopback-only."""

from __future__ import annotations

from realai import PROVIDER_CONFIGS, RealAI
from realai.cloud_fallback import (
    GENERIC_DEFAULT_LLM_PLACEHOLDER,
    apply_cloud_fallback_to_instance,
    discover_cloud_fallback,
    env_credentials_for_request,
    looks_like_local_model_id,
    missing_generation_message,
    provider_can_call_cloud,
    request_skips_vulkan,
    vulkan_forward_enabled,
)


def _clear_cloud_env(monkeypatch):
    keys = [
        "REALAI_CLOUD_FALLBACK",
        "OPENAI_API_KEY",
        "REALAI_OPENAI_API_KEY",
        "REALAI_ANTHROPIC_API_KEY",
        "ANTHROPIC_API_KEY",
        "REALAI_GROK_API_KEY",
        "XAI_API_KEY",
        "REALAI_GEMINI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "REALAI_OPENROUTER_API_KEY",
        "OPENROUTER_API_KEY",
        "REALAI_MISTRAL_API_KEY",
        "MISTRAL_API_KEY",
        "REALAI_TOGETHER_API_KEY",
        "TOGETHER_API_KEY",
        "REALAI_DEEPSEEK_API_KEY",
        "DEEPSEEK_API_KEY",
        "REALAI_PERPLEXITY_API_KEY",
        "PERPLEXITY_API_KEY",
        "RENDER",
        "RENDER_SERVICE_ID",
        "RENDER_INSTANCE_ID",
        "FLY_APP_NAME",
        "RAILWAY_ENVIRONMENT",
        "RAILWAY_ENVIRONMENT_ID",
        "K_SERVICE",
        "AWS_LAMBDA_FUNCTION_NAME",
        "REALAI_VULKAN_FORWARD",
        "REALAI_VULKAN_BASE",
        "NEXT_PUBLIC_LOCAL_CONSOLE_URL",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)


def test_discover_openai_api_key(monkeypatch):
    _clear_cloud_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-cloud-from-render")
    assert discover_cloud_fallback() == ("openai", "sk-cloud-from-render")


def test_discover_realai_openai_key(monkeypatch):
    _clear_cloud_env(monkeypatch)
    monkeypatch.setenv("REALAI_OPENAI_API_KEY", "sk-realai-openai")
    assert discover_cloud_fallback() == ("openai", "sk-realai-openai")


def test_discover_explicit_provider(monkeypatch):
    _clear_cloud_env(monkeypatch)
    monkeypatch.setenv("REALAI_CLOUD_FALLBACK", "anthropic")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-win")
    monkeypatch.setenv("REALAI_ANTHROPIC_API_KEY", "sk-ant-fallback")
    assert discover_cloud_fallback() == ("anthropic", "sk-ant-fallback")


def test_discover_off(monkeypatch):
    _clear_cloud_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-present")
    monkeypatch.setenv("REALAI_CLOUD_FALLBACK", "off")
    assert discover_cloud_fallback() is None


def test_discover_request_cloud_prefix(monkeypatch):
    _clear_cloud_env(monkeypatch)
    assert discover_cloud_fallback("sk-proj-pasted") == ("openai", "sk-proj-pasted")


def test_hosted_message_is_not_generic_default_llm(monkeypatch):
    _clear_cloud_env(monkeypatch)
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("NEXT_PUBLIC_LOCAL_CONSOLE_URL", "http://127.0.0.1:8001/console")
    msg = missing_generation_message(use_local=True)
    assert "register a local model and set it as default_llm" not in msg.lower()
    assert msg != GENERIC_DEFAULT_LLM_PLACEHOLDER
    assert "Cloud API" in msg
    assert "8001" in msg
    assert "OPENAI_API_KEY" in msg
    assert "~/.realai/local_models.json" in msg


def test_local_message_names_actual_registry(monkeypatch):
    _clear_cloud_env(monkeypatch)
    msg = missing_generation_message(use_local=True)
    assert "register a local model and set it as default_llm, then retry" not in msg.lower()
    assert "~/.realai/local_models.json" in msg
    assert "checkpoints_lora\\registry.json" in msg or "checkpoints_lora/registry.json" in msg.replace("\\", "/")


def test_vulkan_off_on_render(monkeypatch):
    _clear_cloud_env(monkeypatch)
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("REALAI_VULKAN_FORWARD", "auto")
    monkeypatch.setenv("REALAI_VULKAN_BASE", "http://127.0.0.1:8080")
    assert vulkan_forward_enabled() is False


def test_vulkan_force_still_off_on_render(monkeypatch):
    _clear_cloud_env(monkeypatch)
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("REALAI_VULKAN_FORWARD", "force")
    monkeypatch.setenv("REALAI_VULKAN_BASE", "http://127.0.0.1:8080")
    assert vulkan_forward_enabled() is False


def test_vulkan_loopback_ok_on_hive(monkeypatch):
    _clear_cloud_env(monkeypatch)
    monkeypatch.setenv("REALAI_VULKAN_FORWARD", "auto")
    monkeypatch.setenv("REALAI_VULKAN_BASE", "http://127.0.0.1:8080")
    assert vulkan_forward_enabled() is True


def test_vulkan_rejects_non_loopback(monkeypatch):
    _clear_cloud_env(monkeypatch)
    monkeypatch.setenv("REALAI_VULKAN_FORWARD", "auto")
    monkeypatch.setenv("REALAI_VULKAN_BASE", "http://llama.internal:8080")
    assert vulkan_forward_enabled() is False


def test_looks_like_local_model_id():
    assert looks_like_local_model_id("realai-default-coder")
    assert looks_like_local_model_id("qwen2.5-coder-7b-instruct-q5_k_m.gguf")
    assert looks_like_local_model_id("qwen-coder-7b")
    assert not looks_like_local_model_id("gpt-4o-mini")
    assert not looks_like_local_model_id("llama-3.1-70b-instruct")
    assert not looks_like_local_model_id("Qwen/Qwen2.5-7B-Instruct")


def test_env_credentials_explicit_provider_does_not_steal_openai_key(monkeypatch):
    _clear_cloud_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-only")
    assert env_credentials_for_request("anthropic") is None
    assert env_credentials_for_request("realai") == ("openai", "sk-openai-only")
    monkeypatch.setenv("REALAI_ANTHROPIC_API_KEY", "sk-ant-mine")
    assert env_credentials_for_request("anthropic") == ("anthropic", "sk-ant-mine")


def test_provider_can_call_custom_base_url():
    assert provider_can_call_cloud(
        "custom-hive", "tok", "https://hive.example/v1", PROVIDER_CONFIGS
    )
    assert not provider_can_call_cloud("custom-hive", "tok", "", PROVIDER_CONFIGS)
    assert not provider_can_call_cloud("local", "tok", "https://x", PROVIDER_CONFIGS)


def test_chat_completion_uses_cloud_fallback(monkeypatch):
    _clear_cloud_env(monkeypatch)
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fallback")
    monkeypatch.setattr(
        "realai.cloud_fallback.local_default_llm_ready", lambda _manager=None: False
    )

    model = RealAI(provider="local", model_name="realai-default-coder")
    assert model.provider == "openai"
    assert model._provider_model == PROVIDER_CONFIGS["openai"]["default_model"]
    assert model.base_url == PROVIDER_CONFIGS["openai"]["base_url"]

    def fake_call(self, messages, temperature=0.7, max_tokens=None, stream=False):
        assert self.provider == "openai"
        assert self._provider_model == "gpt-4o-mini"
        return {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1,
            "model": self._provider_model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "hello from cloud"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {},
        }

    monkeypatch.setattr(RealAI, "_call_openai_compat", fake_call)
    if model._llm_engine is not None:
        monkeypatch.setattr(model._llm_engine, "is_loaded", lambda: False)

    resp = model.chat_completion([{"role": "user", "content": "hey"}])
    content = resp["choices"][0]["message"]["content"]
    assert content == "hello from cloud"
    assert "default_llm" not in content.lower()
    assert "register a local model" not in content.lower()
    assert resp.get("realai_meta", {}).get("cloud_fallback") is True
    assert resp.get("realai_meta", {}).get("source") == "api"


def test_chat_completion_clear_cloud_error_without_keys(monkeypatch):
    _clear_cloud_env(monkeypatch)
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("REALAI_CLOUD_FALLBACK", "off")
    monkeypatch.setattr(
        "realai.cloud_fallback.local_default_llm_ready", lambda _manager=None: False
    )

    model = RealAI(provider="local", model_name="realai-default-coder")
    if model._llm_engine is not None:
        monkeypatch.setattr(model._llm_engine, "is_loaded", lambda: False)

    resp = model.chat_completion([{"role": "user", "content": "hey"}])
    content = resp["choices"][0]["message"]["content"]
    assert "register a local model and set it as default_llm" not in content.lower()
    assert "Cloud API" in content
    assert "OPENAI_API_KEY" in content


def test_apply_skips_when_local_ready(monkeypatch):
    _clear_cloud_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-present")

    class _Inst:
        provider = None
        api_key = None
        base_url = ""
        model_name = "realai-default-coder"
        _model_manager = None
        _base_url_override = None

    inst = _Inst()
    applied = apply_cloud_fallback_to_instance(inst, PROVIDER_CONFIGS, local_ready=True)
    assert applied is False
    assert inst.provider is None


def test_explicit_together_keeps_llama_model_id(monkeypatch):
    _clear_cloud_env(monkeypatch)
    monkeypatch.setattr(
        "realai.cloud_fallback.local_default_llm_ready", lambda _manager=None: False
    )
    model = RealAI(
        provider="together",
        api_key="together-key",
        model_name="llama-3.1-70b-instruct",
    )
    assert model.provider == "together"
    assert model._provider_model == "llama-3.1-70b-instruct"
    assert model._cloud_fallback_applied is False


def test_empty_local_generation_still_cloud_falls_back(monkeypatch):
    _clear_cloud_env(monkeypatch)
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fallback")
    monkeypatch.setattr(
        "realai.cloud_fallback.local_default_llm_ready", lambda _manager=None: False
    )

    model = RealAI(provider="local", model_name="realai-default-coder")

    def fake_call(self, messages, temperature=0.7, max_tokens=None, stream=False):
        return {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1,
            "model": self._provider_model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "hello from cloud"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {},
        }

    monkeypatch.setattr(RealAI, "_call_openai_compat", fake_call)
    if model._llm_engine is not None:
        monkeypatch.setattr(model._llm_engine, "is_loaded", lambda: True)
        monkeypatch.setattr(
            model._llm_engine, "chat_completion", lambda *a, **k: ""
        )

    resp = model.chat_completion([{"role": "user", "content": "hey"}])
    assert resp["choices"][0]["message"]["content"] == "hello from cloud"
    assert resp.get("realai_meta", {}).get("source") == "api"


def test_empty_local_text_completion_still_cloud_falls_back(monkeypatch):
    _clear_cloud_env(monkeypatch)
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fallback")
    monkeypatch.setattr(
        "realai.cloud_fallback.local_default_llm_ready", lambda _manager=None: False
    )

    model = RealAI(provider="local", model_name="realai-default-coder")

    def fake_call(self, messages, temperature=0.7, max_tokens=None, stream=False):
        return {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1,
            "model": self._provider_model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "hello from cloud"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {},
        }

    monkeypatch.setattr(RealAI, "_call_openai_compat", fake_call)
    if model._llm_engine is not None:
        monkeypatch.setattr(model._llm_engine, "is_loaded", lambda: True)
        monkeypatch.setattr(model._llm_engine, "generate", lambda *a, **k: "")

    resp = model.text_completion("hey")
    assert resp["choices"][0]["text"] == "hello from cloud"
    assert resp.get("realai_meta", {}).get("source") == "api"


def test_custom_base_url_not_rebound_to_openai(monkeypatch):
    _clear_cloud_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-bind")
    monkeypatch.setattr(
        "realai.cloud_fallback.local_default_llm_ready", lambda _manager=None: False
    )
    model = RealAI(
        provider="custom-hive",
        api_key="hive-token",
        base_url="https://hive.example/v1",
        model_name="hive-model",
    )
    assert model.provider == "custom-hive"
    assert model.api_key == "hive-token"
    assert model.base_url == "https://hive.example/v1"
    assert model._cloud_fallback_applied is False
    applied = apply_cloud_fallback_to_instance(
        model, PROVIDER_CONFIGS, local_ready=False
    )
    assert applied is True  # already callable via custom base URL
    assert model.provider == "custom-hive"
    assert model.api_key == "hive-token"


def test_explicit_anthropic_not_rebound_to_openai(monkeypatch):
    _clear_cloud_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-only")
    monkeypatch.setattr(
        "realai.cloud_fallback.local_default_llm_ready", lambda _manager=None: False
    )
    model = RealAI(provider="anthropic", model_name="claude-3-5-haiku-20241022")
    assert model.provider == "anthropic"
    assert model._cloud_fallback_applied is False
    if model._llm_engine is not None:
        monkeypatch.setattr(model._llm_engine, "is_loaded", lambda: False)
    resp = model.chat_completion([{"role": "user", "content": "hey"}])
    assert model.provider == "anthropic"
    assert "hello from cloud" not in (
        resp["choices"][0].get("message", {}).get("content") or ""
    )


def test_request_skips_vulkan_for_custom_and_base_url():
    assert request_skips_vulkan("custom-hive", "https://hive.example/v1") is True
    assert request_skips_vulkan("openai", None) is True
    assert request_skips_vulkan("realai", None) is False
    assert request_skips_vulkan("local", "") is False
    assert request_skips_vulkan(None, None) is False
