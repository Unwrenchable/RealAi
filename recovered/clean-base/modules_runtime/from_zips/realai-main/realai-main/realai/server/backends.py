"""Inference backend abstractions for structured RealAI server."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from realai import RealAI

from .logging_utils import setup_logging

logger = setup_logging()

try:
    from .llama_cli_backend import LlamaCliBackend
except ImportError:
    LlamaCliBackend = None


@dataclass
class SamplingConfig:
    """Unified sampling controls shared across backends."""

    temperature: float = 0.2
    top_p: float = 1.0
    repetition_penalty: float = 1.0
    max_tokens: int = 1024


class InferenceBackend(object):
    """Backend interface for chat generation."""

    name = 'base'

    def available(self):
        return True

    def generate(self, model_path: str, prompt: str, sampling: SamplingConfig):
        raise NotImplementedError


class VLLMBackend(InferenceBackend):
    """GPU-first vLLM backend."""

    name = 'vllm'

    def __init__(self):
        self._engines: Dict[str, object] = {}

    def available(self):
        try:
            import vllm  # noqa: F401
            return True
        except Exception:
            return False

    def generate(self, model_path: str, prompt: str, sampling: SamplingConfig):
        try:
            from vllm import LLM
        except Exception as exc:
            logger.warning('vLLM unavailable for %s: %s', model_path, exc)
            return None
        if model_path not in self._engines:
            self._engines[model_path] = LLM(model=model_path)
        outputs = self._engines[model_path].generate(
            [prompt],
            temperature=sampling.temperature,
            top_p=sampling.top_p,
            max_tokens=sampling.max_tokens,
        )
        return outputs[0].outputs[0].text


class LlamaCppBackend(InferenceBackend):
    """CPU-first llama.cpp backend."""

    name = 'llama.cpp'

    def __init__(self):
        self._engines: Dict[str, object] = {}

    def available(self):
        try:
            from llama_cpp import Llama  # noqa: F401
            return True
        except Exception:
            return False

    def generate(self, model_path: str, prompt: str, sampling: SamplingConfig):
        try:
            from llama_cpp import Llama
        except Exception as exc:
            logger.warning('llama.cpp unavailable for %s: %s', model_path, exc)
            return None
        if model_path not in self._engines:
            self._engines[model_path] = Llama(model_path=model_path)
        output = self._engines[model_path](
            prompt,
            max_tokens=sampling.max_tokens,
            temperature=sampling.temperature,
            top_p=sampling.top_p,
            repeat_penalty=sampling.repetition_penalty,
        )
        choices = output.get('choices', [])
        if not choices:
            return None
        return choices[0].get('text')


class RealAIFallbackBackend(InferenceBackend):
    """Legacy fallback backend based on RealAI runtime."""

    name = 'realai-fallback'

    def generate(self, model_path: str, prompt: str, sampling: SamplingConfig):
        model = RealAI(model_name=model_path, provider='local', use_local=True)
        messages = [{'role': 'user', 'content': prompt}]
        response = model.chat_completion(
            messages=messages,
            temperature=sampling.temperature,
            max_tokens=sampling.max_tokens,
            stream=False,
        )
        return response['choices'][0]['message']['content']


class BackendResolver(object):
    """Select and execute an inference backend by policy."""

    def __init__(self):
        self._vllm = VLLMBackend()
        self._llama_cpp = LlamaCppBackend()
        self._llama_cli = LlamaCliBackend() if LlamaCliBackend is not None else None
        self._fallback = RealAIFallbackBackend()

    def select_backend(self, backend_hint: str):
        hint = (backend_hint or '').lower()
        if hint == 'vllm' and self._vllm.available():
            return self._vllm
        if hint in ('llama.cpp', 'llamacpp') and self._llama_cpp.available():
            return self._llama_cpp
        if hint in ('llama-cli', 'llamacli') and self._llama_cli and self._llama_cli.available():
            return self._llama_cli
        # Auto-select best available backend
        if self._vllm.available():
            return self._vllm
        if self._llama_cpp.available():
            return self._llama_cpp
        if self._llama_cli and self._llama_cli.available():
            return self._llama_cli
        return self._fallback

    def generate(self, backend_hint: str, model_path: str, prompt: str, sampling: SamplingConfig):
        backend = self.select_backend(backend_hint)
        text = backend.generate(model_path, prompt, sampling)
        if text is not None:
            return text, backend.name
        text = self._fallback.generate(model_path, prompt, sampling)
        return text, self._fallback.name


RESOLVER = BackendResolver()

