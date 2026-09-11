import json
from pathlib import Path

class PluginSystem:
    def __init__(self, plugins_dir: Path):
        self.plugins_dir = plugins_dir
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.plugins = self._load()

    def _load(self):
        plugins = {}
        for p in self.plugins_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                plugins[data.get("name", p.stem)] = data
            except:
                continue
        print(f"[Plugins] loaded: {list(plugins.keys())}")
        return plugins

    def register(self, name, config):
        self.plugins[name] = config
        out = self.plugins_dir / f"{name}.json"
        out.write_text(json.dumps(config, indent=2), encoding="utf-8")
        print(f"[Plugins] registered {name}")

    def get(self, name):
        return self.plugins.get(name, {})
