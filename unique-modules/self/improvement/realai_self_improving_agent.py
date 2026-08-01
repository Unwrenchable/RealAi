import requests
import json
from pathlib import Path
from typing import List, Dict, Optional

class AutonomousRealAIAgent:
    def __init__(self, base_url: str = "http://127.0.0.1:8000/v1"):
        self.base_url = base_url
        self.model = "hugging-quants/Llama-3.2-1B-Instruct-Q4_K_M-GGUF:Q4_K_M"  # Upgrade this!
    
    def chat(self, messages: List[Dict]):
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.25,
                    "max_tokens": 2048
                },
                timeout=90
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print("LLM Error:", e)
            return None

    def read_file(self, file_path: str) -> str:
        try:
            return Path(file_path).read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading file: {e}"

    def write_file(self, file_path: str, content: str):
        try:
            Path(file_path).write_text(content, encoding="utf-8")
            print(f"✅ Updated file: {file_path}")
        except Exception as e:
            print(f"❌ Failed to write {file_path}: {e}")

    def improve_file(self, file_path: str, goal: str = "Make this code better, cleaner, and more robust", iterations: int = 2):
        print(f"=== Improving {file_path} ===\n")
        
        original_code = self.read_file(file_path)
        
        system = """You are RealAI Agent — an autonomous self-improving coding agent.
You can read and edit files directly. Always strive to make code cleaner, more correct, and production-ready.
When improving: fix bugs, improve structure, add error handling, follow best practices."""

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Here is the current code in {file_path}:\n\n{original_code}\n\nGoal: {goal}\n\nAnalyze it and provide an improved version."}
        ]

        for i in range(iterations):
            print(f"\n--- Iteration {i+1}/{iterations} ---")
            response = self.chat(messages)
            if not response:
                break
            print(response[:800] + "..." if len(response) > 800 else response)  # Preview

            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": "Now output ONLY the complete improved file content. No explanations."})

        # Final version
        final_response = self.chat(messages)
        if final_response:
            # Try to extract code if wrapped in markdown
            if "```python" in final_response:
                final_code = final_response.split("```python")[1].split("```")[0].strip()
            elif "```" in final_response:
                final_code = final_response.split("```")[1].split("```")[0].strip()
            else:
                final_code = final_response.strip()
            
            self.write_file(file_path, final_code)
            print(f"\n✅ Finished improving {file_path}")
        else:
            print("Failed to get final version.")

# ============== USAGE ==============
if __name__ == "__main__":
    agent = AutonomousRealAIAgent()
    
    # Example: Improve one of your files
    agent.improve_file("test_llama.py", goal="Make this code cleaner and add better error handling", iterations=2)
    
    # Or improve the FastAPI endpoint file directly
    # agent.improve_file("main.py", goal="Improve the FastAPI endpoint that talks to llama.cpp", iterations=2)