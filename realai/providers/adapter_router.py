import json
from pathlib import Path

class AdapterRouter:
    def __init__(self, peft_list_path):
        self.adapters = [line.strip() for line in Path(peft_list_path).read_text().splitlines()]

    def route(self, task):
        task = task.lower()

        if "code" in task:
            return [a for a in self.adapters if "code" in a.lower()]

        if "analysis" in task:
            return [a for a in self.adapters if "analysis" in a.lower()]

        if "world" in task or "model" in task:
            return [a for a in self.adapters if "world" in a.lower()]

        return self.adapters  # fallback
