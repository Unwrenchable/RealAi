import requests

class RealAIClient:
    def __init__(self, base_url="http://localhost:8000/v1", api_key=None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def chat(self, messages, model="realai-1.0"):
        payload = {
            "model": model,
            "messages": messages
        }

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        r = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
        return r.json()
