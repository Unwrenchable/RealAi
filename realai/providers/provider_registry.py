"""Default model loader used by abilities (architect_mode, etc.)."""

from __future__ import annotations

import os
from typing import Any, List, Optional


class LocalCompletionModel:
    """Thin adapter so abilities can call create_completion() like llama.cpp."""

    def create_completion(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        n: int = 1,
        stop: Optional[List[str]] = None,
        **_: Any,
    ) -> str:
        from realai.providers.local_llama import local_llama_chat, local_llama_completion

        _ = n
        last_err: Exception | None = None
        # Instruct models (Qwen, Llama-3, etc.) need the chat template.
        try:
            chat = local_llama_chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=int(max_tokens),
                temperature=float(temperature),
            )
            raw = chat.get("raw") or {}
            choices = raw.get("choices") or []
            if choices:
                msg = choices[0].get("message") or {}
                text = str(msg.get("content") or choices[0].get("text") or "").strip()
                if text:
                    return text
        except Exception as e:
            last_err = e
        try:
            result = local_llama_completion(
                prompt=prompt,
                max_tokens=int(max_tokens),
                temperature=float(temperature),
                stop=list(stop) if stop else None,
            )
            text = str(result.get("content") or "").strip()
            if text:
                return text
        except Exception as e:
            last_err = e
        if last_err:
            raise last_err
        return ""


class ProviderRegistry:
    def load_default_model(self) -> LocalCompletionModel | None:
        from realai.providers.local_llama import local_llama_health

        health = local_llama_health()
        if not health.get("ok"):
            try:
                from realai.cli.craft import ensure_gpu_server

                wait = int(os.environ.get("REALAI_GPU_WAIT") or "90")
                started = ensure_gpu_server(wait_s=wait)
                if not started.get("ok"):
                    return None
            except Exception:
                return None
            health = local_llama_health()
            if not health.get("ok"):
                return None
        return LocalCompletionModel()


provider_registry = ProviderRegistry()
