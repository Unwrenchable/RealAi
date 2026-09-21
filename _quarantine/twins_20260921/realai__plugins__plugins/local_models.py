"""
Local AI Model Management for RealAI

This module provides infrastructure for running AI models locally without
relying on external API providers. Supports:
- Local LLM inference (llama.cpp, transformers)
- Local embeddings (sentence-transformers)
- Local image generation (Stable Diffusion)
- Local audio processing (Whisper)

This makes RealAI truly independent and private.
"""

import os
import json
import hashlib
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from enum import Enum


class LocalModelType(Enum):
    """Types of local models supported."""
    LLM = "llm"  # Large Language Models
    EMBEDDING = "embedding"  # Text embedding models
    IMAGE_GEN = "image_generation"  # Image generation models
    IMAGE_ANALYSIS = "image_analysis"  # Vision models
    AUDIO_STT = "audio_stt"  # Speech-to-text
    AUDIO_TTS = "audio_tts"  # Text-to-speech


class LocalModelManager:
    """
    Manages local AI models: downloading, caching, loading, and inference.

    Models are stored in ~/.realai/models/ by default.
    Configuration is stored in ~/.realai/local_models.json
    """

    def __init__(self, models_dir: Optional[str] = None):
        """
        Initialize the local model manager.

        Args:
            models_dir: Directory to store models. Defaults to ~/.realai/models/
        """
        if models_dir is None:
            models_dir = os.path.expanduser("~/.realai/models")

        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self.config_file = self.models_dir.parent / "local_models.json"
        self.config = self._load_config()

        # Cache for loaded models to avoid reloading
        self._loaded_models: Dict[str, Any] = {}

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from disk."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass

        # Default configuration
        return {
            "default_llm": None,
            "default_embedding": "all-MiniLM-L6-v2",
            "models": {},
            "preferences": {
                "use_local_first": True,  # Prefer local models over API calls
                "gpu_enabled": True,
                "max_memory_gb": 8
            }
        }

    def _save_config(self):
        """Save configuration to disk."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config: {e}")

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        return self.config.get("preferences", {}).get(key, default)

    def set_preference(self, key: str, value: Any):
        """Set a user preference."""
        if "preferences" not in self.config:
            self.config["preferences"] = {}
        self.config["preferences"][key] = value
        self._save_config()

    def list_models(self, model_type: Optional[LocalModelType] = None) -> List[Dict[str, Any]]:
        """
        List all downloaded/configured local models.

        Args:
            model_type: Filter by model type. If None, list all models.

        Returns:
            List of model info dictionaries
        """
        models = []
        for name, info in self.config.get("models", {}).items():
            if model_type is None or info.get("type") == model_type.value:
                models.append({
                    "name": name,
                    **info
                })
        return models

    def register_model(self, name: str, model_type: LocalModelType,
                      config: Dict[str, Any]):
        """
        Register a local model in the configuration.

        Args:
            name: Unique name for the model
            model_type: Type of model
            config: Model configuration (path, parameters, etc.)
        """
        if "models" not in self.config:
            self.config["models"] = {}

        self.config["models"][name] = {
            "type": model_type.value,
            **config
        }
        self._save_config()

    def get_model_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a registered model."""
        return self.config.get("models", {}).get(name)

    def is_model_available(self, name: str) -> bool:
        """Check if a model is available (downloaded and configured)."""
        info = self.get_model_info(name)
        if not info:
            return False

        # Check if model file exists
        model_path = info.get("path")
        if model_path:
            return Path(model_path).exists()

        return True


class LocalLLMEngine:
    """
    Local LLM inference engine supporting multiple backends:
    - llama-cpp-python (GGUF models, CPU/GPU)
    - transformers (Hugging Face models)
    - ollama (if available)
    """

    def __init__(self, model_manager: LocalModelManager):
        """
        Initialize the LLM engine.

        Args:
            model_manager: Model manager instance
        """
        self.model_manager = model_manager
        self._llama_cpp = None
        self._transformers = None
        self._current_model = None
        self._current_backend = None

    def _check_llama_cpp(self) -> bool:
        """Check if llama-cpp-python is available."""
        try:
            import llama_cpp
            return True
        except ImportError:
            return False

    def _check_transformers(self) -> bool:
        """Check if transformers is available."""
        try:
            import transformers
            return True
        except ImportError:
            return False

    def load_model(self, model_name: str) -> bool:
        """
        Load a local LLM model.

        Args:
            model_name: Name of the model to load

        Returns:
            True if successful, False otherwise
        """
        info = self.model_manager.get_model_info(model_name)
        if not info:
            return False

        backend = info.get("backend", "llama-cpp")

        if backend == "llama-cpp":
            return self._load_llama_cpp(model_name, info)
        elif backend == "transformers":
            return self._load_transformers(model_name, info)

        return False

    def _load_llama_cpp(self, model_name: str, info: Dict[str, Any]) -> bool:
        """Load a model using llama-cpp-python."""
        try:
            from llama_cpp import Llama

            model_path = info.get("path")
            if not model_path or not Path(model_path).exists():
                return False

            # Configuration
            n_ctx = info.get("context_length", 2048)
            n_gpu_layers = info.get("gpu_layers", 0)
            if self.model_manager.get_preference("gpu_enabled"):
                n_gpu_layers = info.get("gpu_layers", -1)  # -1 = all layers on GPU

            self._llama_cpp = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                verbose=False
            )
            self._current_model = model_name
            self._current_backend = "llama-cpp"
            return True

        except Exception as e:
            print(f"Failed to load llama-cpp model: {e}")
            return False

    def _load_transformers(self, model_name: str, info: Dict[str, Any]) -> bool:
        """Load a model using Hugging Face transformers."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch

            model_id = info.get("model_id")
            if not model_id:
                return False

            device = "cuda" if torch.cuda.is_available() and self.model_manager.get_preference("gpu_enabled") else "cpu"

            self._transformers = {
                "tokenizer": AutoTokenizer.from_pretrained(model_id),
                "model": AutoModelForCausalLM.from_pretrained(
                    model_id,
                    device_map=device,
                    torch_dtype=torch.float16 if device == "cuda" else torch.float32
                )
            }
            self._current_model = model_name
            self._current_backend = "transformers"
            return True

        except Exception as e:
            print(f"Failed to load transformers model: {e}")
            return False

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None
    ) -> str:
        """
        Generate text using the loaded model.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            stop: Stop sequences

        Returns:
            Generated text
        """
        if self._current_backend == "llama-cpp" and self._llama_cpp:
            return self._generate_llama_cpp(prompt, max_tokens, temperature, top_p, stop)
        elif self._current_backend == "transformers" and self._transformers:
            return self._generate_transformers(prompt, max_tokens, temperature, top_p, stop)

        return ""

    def _generate_llama_cpp(self, prompt: str, max_tokens: int,
                           temperature: float, top_p: float,
                           stop: Optional[List[str]]) -> str:
        """Generate using llama-cpp backend."""
        try:
            result = self._llama_cpp(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=stop or [],
                echo=False
            )
            return result["choices"][0]["text"]
        except Exception as e:
            print(f"Generation error: {e}")
            return ""

    def _generate_transformers(self, prompt: str, max_tokens: int,
                              temperature: float, top_p: float,
                              stop: Optional[List[str]]) -> str:
        """Generate using transformers backend."""
        try:
            import torch

            tokenizer = self._transformers["tokenizer"]
            model = self._transformers["model"]

            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True
            )

            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Remove the prompt from the output
            if generated_text.startswith(prompt):
                generated_text = generated_text[len(prompt):]

            return generated_text.strip()

        except Exception as e:
            print(f"Generation error: {e}")
            return ""

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> str:
        """
        Generate a chat completion from messages.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter

        Returns:
            Generated response text
        """
        # Format messages into a prompt
        prompt = self._format_chat_prompt(messages)
        return self.generate(prompt, max_tokens, temperature, top_p)

    def _format_chat_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Format chat messages into a prompt string.
        Uses a simple format that works with most models.
        """
        prompt_parts = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")

        # Add the final assistant prompt
        prompt_parts.append("Assistant:")

        return "\n\n".join(prompt_parts)

    def is_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        return self._current_model is not None

    def get_current_model(self) -> Optional[str]:
        """Get the name of the currently loaded model."""
        return self._current_model

    def unload(self):
        """Unload the current model to free memory."""
        self._llama_cpp = None
        self._transformers = None
        self._current_model = None
        self._current_backend = None


# Singleton instances
_model_manager: Optional[LocalModelManager] = None
_llm_engine: Optional[LocalLLMEngine] = None
_singleton_lock = threading.Lock()


def get_model_manager() -> LocalModelManager:
    """Get or create the global model manager instance (thread-safe)."""
    global _model_manager
    if _model_manager is None:
        with _singleton_lock:
            if _model_manager is None:
                _model_manager = LocalModelManager()
    return _model_manager


def get_llm_engine() -> LocalLLMEngine:
    """Get or create the global LLM engine instance (thread-safe)."""
    global _llm_engine
    if _llm_engine is None:
        with _singleton_lock:
            if _llm_engine is None:
                _llm_engine = LocalLLMEngine(get_model_manager())
    return _llm_engine
