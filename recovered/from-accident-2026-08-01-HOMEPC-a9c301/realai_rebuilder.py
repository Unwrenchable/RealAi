import requests
from pathlib import Path
from typing import List, Dict

class RealAIRebuilder:
    def __init__(self, base_url: str = "http://127.0.0.1:8000/v1"):
        self.base_url = base_url
        self.model = "bartowski/Llama-3.2-3B-Instruct-GGUF:Llama-3.2-3B-Instruct-Q5_K_M.gguf"
    
    def chat(self, messages: List[Dict], max_tokens: int = 8192):
        try:
            resp = requests.post(f"{self.base_url}/chat/completions", json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.18,
                "max_tokens": max_tokens
            }, timeout=200)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print("Error:", e)
            return None

    def rebuild(self):
        print("=== RealAI True Rebuilder Activated ===\n")
        
        # Load your capabilities reference if it exists
        ref_path = Path("CAPABILITIES.md")
        ref_content = ref_path.read_text(encoding="utf-8") if ref_path.exists() else "No reference file found."
        
        system = """You are the RealAI Architect. 
Your mission is to build the real thing — a unique, powerful, multi-modal, self-improving agentic framework.
Focus on making it stand out from other projects."""

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"""Here is the full RealAI Capabilities Reference:\n\n{ref_content}\n\n
Current project state: Many plugins seem missing.
Plan and start building:
1. Recommended folder structure for full RealAI
2. Priority files to create/recover (especially plugins)
3. How to implement core capabilities like memory, multi-agent, plugin system, self-reflection
Output a clear action plan."""}
        ]

        plan = self.chat(messages)
        print(plan)

        # TODO: Next iterations will execute the plan (create folders, files, etc.)

if __name__ == "__main__":
    rebuilder = RealAIRebuilder()
    rebuilder.rebuild()