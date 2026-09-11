import json
from pathlib import Path

class WorldModel:
    def __init__(self, path: Path):
        self.path = path
        self.state = self._load()

    def _load(self):
        if not self.path.exists():
            return {"version": 1, "data": {}}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except:
            return {"version": 1, "data": {}}

    def update(self, key, value):
        self.state["data"][key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        print(f"[WorldModel] updated {key}")

    def snapshot(self):
        return self.state
