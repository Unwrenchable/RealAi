import requests
from pathlib import Path
from typing import List, Dict

class RealAIFullAutonomous:
    def __init__(self, base_url: str = "http://127.0.0.1:8000/v1"):
        self.base_url = base_url
        self.model = "bartowski/Llama-3.2-3B-Instruct-GGUF:Llama-3.2-3B-Instruct-Q5_K_M.gguf"
    
    def chat(self, messages: List[Dict], max_tokens: int = 8192):
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json={"model": self.model, "messages": messages, "temperature": 0.2, "max_tokens": max_tokens},
                timeout=180
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print("Error:", e)
            return None

    def explore_project(self, root: str = ".") -> str:
        """Safely build project structure"""
        ignore = {".venv", "__pycache__", ".git", ".cache", "node_modules", "models"}
        structure = []
        try:
            for path in sorted(Path(root).rglob("*")):
                try:
                    if path.is_file() and not any(ign in path.parts for ign in ignore):
                        structure.append(str(path.relative_to(root)))
                        if len(structure) >= 120:
                            break
                except (OSError, PermissionError):
                    continue  # Skip problematic files/symlinks
        except Exception as e:
            structure.append(f"Error exploring: {e}")
        return "\n".join(structure)

    def improve_file(self, file_path: Path, goal: str):
        try:
            original = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            print(f"❌ Could not read {file_path.name}")
            return
        
        system = "You are RealAI Agent. Output ONLY the complete improved Python code. No explanations."
        
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"File: {file_path.name}\n\n{original}\n\nTask: {goal}"}
        ]
        
        final = self.chat(messages)
        if final:
            if "```" in final:
                final = final.split("```python")[-1].split("```")[0] if "```python" in final else final.split("```")[-1].split("```")[0]
            try:
                file_path.write_text(final.strip(), encoding="utf-8")
                print(f"✅ Improved: {file_path.name}")
            except Exception as e:
                print(f"❌ Failed to write {file_path.name}: {e}")
        else:
            print(f"❌ No response for {file_path.name}")

    def run_full_improvement(self, root: str = ".", max_files: int = 10):
        print("=== RealAI Full Autonomous Agent Starting ===\n")
        
        print("Analyzing project structure...")
        structure = self.explore_project(root)
        
        analysis = self.chat([
            {"role": "system", "content": "You are RealAI Architect."},
            {"role": "user", "content": f"Project structure:\n{structure}\n\nSuggest improvements for a proper RealAI layered framework."}
        ])
        
        print("\n=== Architecture Analysis ===\n")
        print(analysis[:1500] + "..." if analysis else "No analysis")

        print("\n=== Improving Files ===\n")
        py_files = [p for p in Path(root).rglob("*.py") if not any(ign in p.parts for ign in [".venv", "__pycache__", "node_modules"])][:max_files]
        
        for file_path in py_files:
            self.improve_file(file_path, "Improve code quality, structure, error handling, and alignment with RealAI agentic design.")

        print("\n=== Full Improvement Cycle Complete ===")

if __name__ == "__main__":
    agent = RealAIFullAutonomous()
    agent.run_full_improvement(".", max_files=8)   # Keep small at first