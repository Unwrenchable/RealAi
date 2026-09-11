"""
Thin adapter: LocalLLMEngine-style API over the Vulkan llama-server.
"""
import json
import urllib.request
from typing import Optional, List, Dict, Any

DEFAULT_BASE = "http://127.0.0.1:8080/v1"
DEFAULT_MODEL = "qwen2.5-coder-7b-instruct-q5_k_m.gguf"

class VulkanHTTPEngine:
    def __init__(self, base_url: str = DEFAULT_BASE, model: str = DEFAULT_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._loaded = True  # server already has the model

    def is_loaded(self) -> bool:
        return self._loaded

    def get_current_model(self) -> str:
        return self.model

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 256,
        temperature: float = 0.7,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"]

    def generate(self, prompt: str, max_tokens: int = 128) -> str:
        return self.chat_completion(
            [{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )

if __name__ == "__main__":
    eng = VulkanHTTPEngine()
    print("model:", eng.get_current_model())
    print(eng.generate("In one sentence, what can RealAI self-improvement do?"))
