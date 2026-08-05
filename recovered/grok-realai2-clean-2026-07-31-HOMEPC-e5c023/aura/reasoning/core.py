"""
AURA Reasoning Engine for RealAI
Uses local LLM to break down user requests into actionable plans.
"""

import requests
import json
from typing import List, Dict

class ReasoningEngine:
    """
    Main reasoning component. Plans actions based on user input and memory.
    """
    def __init__(self, api_base_url: str = "http://127.0.0.1:8000/v1"):
        self.api_base_url = api_base_url
        self.model_name = "local-model"  # Adjust if needed

    def create_plan(self, user_input: str, memories: List[str] = None) -> Dict:
        """
        Generate a structured plan using the local LLM.
        """
        if memories is None:
            memories = []

        system_prompt = f"""
You are Aura, a reasoning engine for RealAI.
Your job is to turn a user request into a concrete plan by choosing the best skill.

Respond with valid JSON only in this exact format:
{{
  "thought": "Brief reasoning",
  "skill": "skill_name",
  "params": {{ "param": "value" }}
}}

Available skills include:
- file_io.read_file, file_io.write_file
- code.introspect, code.modify
- web.search
- core.noop (do nothing)

Relevant memories:
{chr(10).join('- ' + m for m in memories)}

User Request: {user_input}
"""

        try:
            response = requests.post(
                f"{self.api_base_url}/chat/completions",
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": system_prompt}],
                    "temperature": 0.1,
                    "max_tokens": 1024,
                },
                timeout=60
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]

            # Extract JSON
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = content[start:end]
                plan = json.loads(json_str)
                return plan
            else:
                raise ValueError("No JSON found")
        except Exception as e:
            print(f"Reasoning error: {e}")
            return {"thought": "Error during reasoning.", "skill": "core.noop", "params": {}}

# Singleton
_reasoner = None

def get_reasoner() -> ReasoningEngine:
    global _reasoner
    if _reasoner is None:
        _reasoner = ReasoningEngine()
    return _reasoner