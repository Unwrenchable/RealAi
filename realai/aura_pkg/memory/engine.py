"""
AURA Memory Engine for RealAI
Long-term and working memory with future extensibility (FAISS, SQLite, etc.).
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

class LongTermMemory:
    """Persistent long-term memory using files (easy to upgrade to vector DB)."""
    
    def __init__(self, memory_path: str = "aura/memory_store"):
        self.memory_path = Path(memory_path)
        self.memory_path.mkdir(parents=True, exist_ok=True)
    
    def remember(self, experience: str, metadata: Optional[Dict] = None):
        """Save an experience with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        entry = {
            "timestamp": timestamp,
            "experience": experience,
            "metadata": metadata or {}
        }
        filename = self.memory_path / f"exp_{timestamp}.json"
        filename.write_text(json.dumps(entry, indent=2, ensure_ascii=False), encoding="utf-8")
    
    def recall(self, query: str = "", top_k: int = 10) -> List[Dict]:
        """Recall recent or relevant memories."""
        try:
            files = sorted(
                self.memory_path.glob("exp_*.json"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            memories = []
            for f in files[:top_k]:
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    memories.append(data)
                except:
                    continue
            return memories
        except Exception as e:
            print(f"Memory recall error: {e}")
            return []

class WorkingMemory:
    """Short-term working memory for current context."""
    def __init__(self, max_results: int = 20):
        self.current_plan = None
        self.current_action = None
        self.recent_results: List[Any] = []
        self.max_results = max_results
        self.context: Dict[str, Any] = {}

    def update_plan(self, plan: str):
        self.current_plan = plan

    def add_result(self, result: Any):
        self.recent_results.append(result)
        if len(self.recent_results) > self.max_results:
            self.recent_results.pop(0)

    def add_context(self, key: str, value: Any):
        self.context[key] = value

    def get_context(self) -> Dict:
        return self.context

# Global instances
long_term_memory = LongTermMemory()
working_memory = WorkingMemory()

def get_memory():
    """Main entry point for RealAI."""
    return {
        "long_term": long_term_memory,
        "working": working_memory
    }