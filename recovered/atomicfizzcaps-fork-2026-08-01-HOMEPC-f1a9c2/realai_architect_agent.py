import requests
from pathlib import Path
import json
from typing import List, Dict

class RealAIArchitect:
    def __init__(self, base_url: str = "http://127.0.0.1:8000/v1"):
        self.base_url = base_url
        self.model = "hugging-quants/Llama-3.2-1B-Instruct-Q4_K_M-GGUF:Q4_K_M"
    
    def chat(self, messages: List[Dict]):
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json={"model": self.model, "messages": messages, "temperature": 0.2, "max_tokens": 2048},
                timeout=120
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print("Error:", e)
            return None

    def explore_project(self, root: str = ".") -> str:
        """Build a summary of the project structure"""
        structure = []
        for path in Path(root).rglob("*"):
            if path.is_file() and not any(x in path.parts for x in [".venv", "__pycache__", ".git", ".cache"]):
                rel = path.relative_to(root)
                structure.append(str(rel))
        return "\n".join(structure[:100])  # Limit for context

    def improve_architecture(self, root_dir: str = ".", focus: str = "RealAI framework"):
        print("=== RealAI Autonomous Architect Starting ===\n")
        
        structure = self.explore_project(root_dir)
        
        system = """You are RealAI Architect — an autonomous system that understands project structure, 
improves architecture, moves files to logical locations, and wires components together for a clean, layered RealAI setup."""

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"""Project structure:\n{structure}\n\nGoal: Improve this as a RealAI framework.
Suggest:
1. Better folder structure (core, agents, plugins, memory, utils, etc.)
2. Which files should be moved where
3. Key improvements to make it more agentic and layered.
Output in clear markdown with sections."""}
        ]

        print("Analyzing architecture...")
        analysis = self.chat(messages)
        print(analysis)

        # TODO: Add file moving + batch improvements in future iterations
        print("\nFor now, this gives the blueprint. Next step: implement auto-restructuring.")

if __name__ == "__main__":
    architect = RealAIArchitect()
    architect.improve_architecture(".")