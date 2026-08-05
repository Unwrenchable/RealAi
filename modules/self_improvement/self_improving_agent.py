import requests
from typing import List, Dict

class SelfImprovingAgent:
    def __init__(self, base_url: str = "http://127.0.0.1:8000/v1"):
        self.base_url = base_url
        # Update this when you switch models
        self.model = "hugging-quants/Llama-3.2-1B-Instruct-Q4_K_M-GGUF:Q4_K_M"
    
    def chat(self, messages: List[Dict], max_tokens: int = 2048):
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.25,
            "max_tokens": max_tokens
        }
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions", 
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print("Error communicating with llama-server:", e)
            return None

    def improve_code(self, task: str, iterations: int = 3):
        print("=== RealAI Self-Improving Agent ===\n")
        
        # Stronger system prompt
        system = """You are RealAI Agent — a self-improving, autonomous coding agent.
Core rules:
- Think step-by-step
- Write clean, modern, production-ready Python code
- Always use HTTP calls to the llama.cpp server[](http://127.0.0.1:8000/v1) when needed
- After writing code, critically review and fix it
- Focus on correctness, error handling, and simplicity"""

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": task}
        ]

        for i in range(iterations):
            print(f"\n--- Iteration {i+1}/{iterations} ---")
            response = self.chat(messages)
            if not response:
                print("No response received.")
                break
                
            print(response)
            
            # Self-critique instruction
            critique = "Review the code you just produced. Identify bugs, improve structure, error handling, and performance. Then output the improved version of the code."
            
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": critique})

        print("\n=== Final Improved Version ===")
        final = self.chat(messages)
        if final:
            print(final)
        return final


# ============== USAGE ==============
if __name__ == "__main__":
    agent = SelfImprovingAgent()
    
    task = """Write a FastAPI endpoint that takes a user prompt, sends it to the local llama.cpp server 
via HTTP POST to /v1/chat/completions, and returns the generated response as JSON. 
Include proper async handling and error handling."""
    
    agent.improve_code(task, iterations=2)