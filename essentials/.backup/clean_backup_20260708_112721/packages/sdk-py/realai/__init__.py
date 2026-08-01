"""
RealAI Python SDK
OpenAI-compatible client for RealAI platform
"""

import requests
from typing import Optional, List, Dict, Any


class RealAI:
    """RealAI Python client"""

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = (base_url or "https://api.realai.com").rstrip("/")

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Send a chat completion request to RealAI"""
        payload = {
            "model": model,
            "messages": messages,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def models(self) -> Dict[str, Any]:
        """List available models"""
        response = requests.get(
            f"{self.base_url}/v1/models",
            headers={
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        response.raise_for_status()
        return response.json()
