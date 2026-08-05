"""
Local llama.cpp / Vulkan backend client.

Default target is RealAI's Vulkan llama-server on :8080
(override with REALAI_VULKAN_BASE or LOCAL_LLAMA_URL).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

BASE_URL = (
    os.environ.get("LOCAL_LLAMA_URL")
    or os.environ.get("REALAI_VULKAN_BASE")
    or "http://127.0.0.1:8080"
).rstrip("/")


def _post_json(path: str, payload: Dict[str, Any], timeout: float = 300.0) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(path: str, timeout: float = 10.0) -> Dict[str, Any]:
    req = urllib.request.Request(f"{BASE_URL}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def local_llama_health() -> Dict[str, Any]:
    """Probe local llama-server health."""
    try:
        body = _get_json("/health", timeout=5.0)
        return {"ok": True, "base": BASE_URL, "body": body}
    except Exception as e:
        return {"ok": False, "base": BASE_URL, "error": str(e)}


def local_llama_completion(
    prompt: str,
    max_tokens: int = 512,
    temperature: float = 0.7,
    stop: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Completions-style call against llama.cpp native /completion
    (falls back to OpenAI /v1/completions if needed).
    """
    payload = {
        "prompt": prompt,
        "n_predict": max_tokens,
        "temperature": temperature,
        "stop": stop or [],
        "stream": False,
    }
    try:
        data = _post_json("/completion", payload)
        content = data.get("content")
        if isinstance(content, list):
            text = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        else:
            text = str(content or data.get("text") or "")
        return {"content": text, "raw": data, "endpoint": "/completion", "base": BASE_URL}
    except Exception:
        # OpenAI-compatible fallback
        oai = {
            "model": os.environ.get("REALAI_BACKEND_MODEL", "local"),
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stop": stop or [],
        }
        data = _post_json("/v1/completions", oai)
        choices = data.get("choices") or []
        text = (choices[0].get("text") if choices else "") or ""
        return {"content": text, "raw": data, "endpoint": "/v1/completions", "base": BASE_URL}


def local_llama_chat(
    messages: List[Dict[str, str]],
    max_tokens: int = 512,
    temperature: float = 0.7,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """OpenAI-compatible chat completions against local llama-server."""
    payload = {
        "model": model or os.environ.get("REALAI_BACKEND_MODEL", "local"),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    data = _post_json("/v1/chat/completions", payload)
    return {"raw": data, "base": BASE_URL, "endpoint": "/v1/chat/completions"}
