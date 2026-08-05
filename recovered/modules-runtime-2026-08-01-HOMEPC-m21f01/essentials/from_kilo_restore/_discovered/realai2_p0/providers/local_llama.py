import os
import requests
from realai.providers.local_llama import local_llama_completion
from typing import List, Dict, Any

# Base URL for your running llama-server
BASE_URL = os.getenv("LOCAL_LLAMA_URL", "http://127.0.0.1:8000")

def local_llama_completion(
    prompt: str,
    max_tokens: int = 512,
    temperature: float = 0.7,
    stop: List[str] | None = None,
) -> Dict[str, Any]:
    """Send a prompt to your local llama-server and return the response."""
    payload = {
        "prompt": prompt,
        "n_predict": max_tokens,
        "temperature": temperature,
        "stop": stop or [],
        "stream": False,
    }

    resp = requests.post(f"{BASE_URL}/completion", json=payload, timeout=300)
    resp.raise_for_status()
    data = resp.json()

    content = "".join(part.get("text", "") for part in data.get("content", []))
    return {"content": content, "raw": data}
