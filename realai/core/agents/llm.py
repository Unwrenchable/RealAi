"""Lazy LLM helper for hierarchical agents.

Prefers the local hive orchestrator (Vulkan via :8001), then optional
OpenAI-compatible keys, then a tiny mock.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional
from urllib.request import Request, urlopen

_llm: Optional[Any] = None


def _hive_base() -> str:
    return (
        os.environ.get("REALAI_API_URL")
        or os.environ.get("REALAI_API_BASE")
        or "http://127.0.0.1:8001"
    ).rstrip("/")


def _hive_complete(messages: list[dict[str, str]], temperature: float = 0.2) -> str:
    payload = {
        "model": os.environ.get("REALAI_DEFAULT_MODEL") or "realai-default-coder",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": int(os.environ.get("REALAI_MAX_TOKENS") or "512"),
    }
    req = Request(
        f"{_hive_base()}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""


class _HiveLLM:
    """Minimal chat client used when langchain is absent."""

    def invoke(self, *args: Any, **kwargs: Any) -> str:
        prompt = ""
        system = "You are a RealAI specialist. Be concise and actionable."
        if args:
            first = args[0]
            if isinstance(first, str):
                prompt = first
            elif isinstance(first, list):
                parts = []
                for m in first:
                    content = getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else str(m))
                    parts.append(str(content))
                prompt = "\n".join(parts)
            else:
                prompt = str(first)
        prompt = str(kwargs.get("input") or kwargs.get("prompt") or prompt)
        try:
            return _hive_complete(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt[:12000]},
                ]
            ) or "hive_empty_response"
        except Exception as e:
            return f"hive_unavailable:{type(e).__name__}:{e}"


def get_llm() -> Any:
    """Return hive/local ChatOpenAI when reachable; otherwise a hive urllib client or mock."""
    global _llm
    if _llm is not None:
        return _llm

    base = _hive_base()
    model_name = os.getenv("REALAI_MODEL") or os.getenv("REALAI_DEFAULT_MODEL") or "realai-default-coder"
    temperature = float(os.getenv("REALAI_TEMPERATURE", "0.2"))
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("REALAI_API_KEY") or "local"

    # 1) langchain pointing at hive (or remote OpenAI if REALAI_USE_OPENAI=1)
    try:
        from langchain_openai import ChatOpenAI  # type: ignore

        use_openai = os.getenv("REALAI_USE_OPENAI", "").lower() in ("1", "true", "yes")
        kwargs: dict[str, Any] = {"model": model_name, "temperature": temperature, "api_key": api_key}
        if not use_openai:
            kwargs["base_url"] = f"{base}/v1"
        _llm = ChatOpenAI(**kwargs)
        return _llm
    except Exception:
        pass

    # 2) direct hive HTTP
    try:
        _hive_complete([{"role": "user", "content": "ping"}], temperature=0)
        _llm = _HiveLLM()
        return _llm
    except Exception:
        pass

    class _Mock:
        def invoke(self, *args: Any, **kwargs: Any) -> str:
            return "Mock response (hive :8001 unreachable; start realai-local)"

    _llm = _Mock()
    return _llm
