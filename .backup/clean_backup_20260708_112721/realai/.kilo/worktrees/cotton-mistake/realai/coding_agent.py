import os
from realai import RealAI

class CodingAgent:
    def __init__(self):
        self.ai = RealAI()
        self.workspace = "/mnt/c/Users/tsmit/realai"

    async def code(self, task: str, file_path: str = None):
        """Main method: Tell RealAI what to build/edit"""
        print(f"[RealAI Coding Agent] Working on: {task}")

        context = f"""
You are an expert coding assistant working on the RealAi + Atomic Fizz project.
Current workspace: {self.workspace}

Task: {task}
"""

        if file_path:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                context += f"\n\nCurrent file ({file_path}):\n```python\n{content}\n```"
            except:
                pass

        response = await self.ai.chat(context + "\n\nProvide complete code solution.", 
                                     temperature=0.7)
        
        print("\n" + "="*60)
        print(response.get("content", "No response"))
        print("="*60)

        return response

# Quick usage
if __name__ == "__main__":
    import asyncio
    agent = CodingAgent()
    asyncio.run(agent.code("Create a new function to generate wasteland NPC dialogue"))
