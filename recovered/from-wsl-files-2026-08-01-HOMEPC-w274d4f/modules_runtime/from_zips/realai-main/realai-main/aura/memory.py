# AURA - Memory System
# Handles long-term and short-term (working) memory.

import os
import json
from datetime import datetime

class LongTermMemory:
    """
    A simple file-based long-term memory system.
    Experiences are stored as timestamped text files.
    """
    def __init__(self, memory_path="aura/memory_store"):
        self.memory_path = memory_path
        os.makedirs(self.memory_path, exist_ok=True)

    def remember(self, experience: str):
        """Saves an experience to a new file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.join(self.memory_path, f"exp_{timestamp}.txt")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(experience)

    def recall(self, query: str, top_k=5) -> list:
        """
        Recalls the most relevant memories.
        This is a very basic implementation that just returns the most recent memories.
        A real implementation would use vector search (e.g., FAISS, ChromaDB).
        """
        try:
            files = sorted(
                [os.path.join(self.memory_path, f) for f in os.listdir(self.memory_path)],
                key=os.path.getmtime,
                reverse=True
            )

            relevant_memories = []
            for f in files[:top_k]:
                with open(f, 'r', encoding='utf-8') as file:
                    relevant_memories.append(file.read())
            return relevant_memories
        except Exception as e:
            print(f"Could not recall memories: {e}")
            return []

class WorkingMemory:
    """
    Holds the current state of the AI's thoughts and actions.
    For now, this is just a placeholder.
    """
    def __init__(self):
        self.current_plan = None
        self.current_action = None
        self.recent_results = []

    def update_plan(self, plan):
        self.current_plan = plan

    def add_result(self, result):
        self.recent_results.append(result)
        if len(self.recent_results) > 10:
            self.recent_results.pop(0)
