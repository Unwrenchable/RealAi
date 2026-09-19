"""
RealAI Local Models Plugin - Fixed for AMD GPU (DirectML)
"""

import os
import json
import hashlib
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional
from enum import Enum

class LocalModelType(Enum):
    LLM = "llm"
    EMBEDDING = "embedding"
    IMAGE_GEN = "image_generation"
    IMAGE_ANALYSIS = "image_analysis"
    AUDIO_STT = "audio_stt"
    AUDIO_TTS = "audio_tts"

class LocalModelManager:
    def __init__(self, models_dir: Optional[str] = None):
        if models_dir is None:
            models_dir = os.path.expanduser("~/.realai/models")
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.models_dir.parent / "local_models.json"
        self.config = self._load_config()
        self._loaded_models: Dict[str, Any] = {}

    def _load_config(self) -> Dict[str, Any]:
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "default_llm": None,
            "default_embedding": "all-MiniLM-L6-v2",
            "models": {},
            "preferences": {
                "use_local_first": True,
                "gpu_enabled": True,  # Force enabled for AMD
                "max_memory_gb": 12
            }
        }

    def _save_config(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config: {e}")

    def get_preference(self, key: str, default: Any = None) -> Any:
        return self.config.get("preferences", {}).get(key, default)

    def set_preference(self, key: str, value: Any):
        if "preferences" not in self.config:
            self.config["preferences"] = {}
        self.config["preferences"][key] = value
        self._save_config()

    # ... keep your other methods (list_models, register_model, etc.)

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Return model metadata used by LocalLLMEngine.

        This repo historically kept model registrations flexible; for the LoRA
        path we provide a direct mapping so `realai_local_server.py` can
        immediately load your adapter.
        """
        if not model_name:
            return None

        # Direct LoRA mapping (override / default)
        if model_name in {"qwen2.5-1.5b-lora", "qwen2.5-1.5b"}:
            return {
                "backend": "peft-transformers",
                "base_model_id": "Qwen/Qwen2.5-1.5B-Instruct",
                "adapter_path": "./checkpoints_lora/qwen2.5-1.5b-lora",
                "context_length": 4096,
            }

        # Try local_models.json registrations if present
        models = self.config.get("models") or {}
        if model_name in models:
            info = models[model_name]
            if isinstance(info, dict):
                return info

        return None

    def get_llm(self, model_name: str = None):
        if model_name is None:
            model_name = self.config.get("default_llm")
        engine = get_llm_engine()
        if engine.load_model(model_name):
            return engine
        return None

class LocalLLMEngine:
    def __init__(self, model_manager: LocalModelManager):
        self.model_manager = model_manager
        self._llama_cpp = None
        self._transformers = None
        self._current_model = None
        self._current_backend = None

    def load_model(self, model_name: str) -> bool:
        info = self.model_manager.get_model_info(model_name)
        if not info:
            return False

        backend = info.get("backend", "llama-cpp")
        if backend == "llama-cpp":
            return self._load_llama_cpp(model_name, info)
        if backend == "peft-transformers":
            return self._load_peft_transformers(model_name, info)
        return False


    def _load_llama_cpp(self, model_name: str, info: Dict[str, Any]) -> bool:
        try:
            from llama_cpp import Llama
            model_path = info.get("path")
            if not model_path or not Path(model_path).exists():
                print(f"Model not found: {model_path}")
                return False
            n_ctx = info.get("context_length", 2048)
            n_gpu_layers = info.get("gpu_layers", -1) if self.model_manager.get_preference("gpu_enabled") else 0
            print(f"Loading with GPU layers: {n_gpu_layers} (AMD DirectML)")
            self._llama_cpp = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                verbose=True
            )
            self._current_model = model_name
            self._current_backend = "llama-cpp"
            print(f"✅ Model loaded with GPU support: {model_name}")
            return True
        except Exception as e:
            print(f"Failed to load llama-cpp model: {e}")
            return False

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7, top_p: float = 0.9, stop: Optional[List[str]] = None) -> str:
        if self._current_backend == "llama-cpp" and self._llama_cpp:
            return self._generate_llama_cpp(prompt, max_tokens, temperature, top_p, stop)
        if self._current_backend == "peft-transformers" and self._transformers:
            return self._generate_peft_transformers(prompt, max_tokens, temperature, top_p, stop)
        return ""

    def _load_peft_transformers(self, model_name: str, info: Dict[str, Any]) -> bool:
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            from peft import PeftModel

            base_model_id = info.get("base_model_id")
            adapter_path = info.get("adapter_path")
            context_length = info.get("context_length", 4096)

            if not base_model_id or not adapter_path:
                print(f"Missing base_model_id/adapter_path for {model_name}")
                return False

            print(f"Loading PEFT model: base={base_model_id}, adapter={adapter_path}")
            tokenizer = AutoTokenizer.from_pretrained(base_model_id, trust_remote_code=True)
            base_model = AutoModelForCausalLM.from_pretrained(
                base_model_id,
                trust_remote_code=True,
                device_map="auto",
                torch_dtype=getattr(torch, info.get("dtype", "bfloat16"), torch.bfloat16),
            )

            model = PeftModel.from_pretrained(base_model, adapter_path)
            model.eval()

            # Store for generation
            self._transformers = {
                "model": model,
                "tokenizer": tokenizer,
                "context_length": context_length,
            }
            self._current_model = model_name
            self._current_backend = "peft-transformers"
            return True
        except Exception as e:
            print(f"Failed to load peft-transformers model: {e}")
            return False

    def _generate_peft_transformers(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
        stop: Optional[List[str]],
    ) -> str:
        try:
            import torch

            pack = self._transformers or {}
            model = pack.get("model")
            tokenizer = pack.get("tokenizer")
            if not model or not tokenizer:
                return ""

            inputs = tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=pack.get("context_length", 4096),
            )

            gen_kwargs = {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "do_sample": temperature is not None and temperature > 0,
            }

            with torch.no_grad():
                output_ids = model.generate(**inputs, **gen_kwargs)

            generated = tokenizer.decode(
                output_ids[0][inputs["input_ids"].shape[-1] :],
                skip_special_tokens=True,
            )

            # naive stop support
            if stop:
                for s in stop:
                    if s in generated:
                        generated = generated.split(s, 1)[0]

            return generated.strip()
        except Exception as e:
            print(f"PEFT generation error: {e}")
            return ""


    def _generate_llama_cpp(self, prompt: str, max_tokens: int, temperature: float, top_p: float, stop: Optional[List[str]]) -> str:
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

    def chat_completion(self, messages: List[Dict[str, str]], max_tokens: int = 512, temperature: float = 0.7, top_p: float = 0.9) -> str:
        prompt = self._format_chat_prompt(messages)
        return self.generate(prompt, max_tokens, temperature, top_p)

    def _format_chat_prompt(self, messages: List[Dict[str, str]]) -> str:
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
        prompt_parts.append("Assistant:")
        return "\n\n".join(prompt_parts)

# Singletons
_model_manager: Optional[LocalModelManager] = None
_llm_engine: Optional[LocalLLMEngine] = None
_singleton_lock = threading.Lock()

def get_model_manager() -> LocalModelManager:
    global _model_manager
    if _model_manager is None:
        with _singleton_lock:
            if _model_manager is None:
                _model_manager = LocalModelManager()
    return _model_manager

def get_llm_engine() -> LocalLLMEngine:
    global _llm_engine
    if _llm_engine is None:
        with _singleton_lock:
            if _llm_engine is None:
                _llm_engine = LocalLLMEngine(get_model_manager())
    return _llm_engine