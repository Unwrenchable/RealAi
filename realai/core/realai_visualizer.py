import json
from pathlib import Path

class RealAIVisualizer:
    """
    Produces a simple ASCII architecture tree from scan results.
    """

    def __init__(self, scan_manifest: Path, out: Path):
        self.scan_manifest = scan_manifest
        self.out = out

    def run(self):
        data = json.loads(self.scan_manifest.read_text(encoding="utf-8"))
        flows = data.get("flows", {})
        lines = []

        def add(title, items):
            lines.append(f"\n=== {title} ===")
            for i in items:
                lines.append(f"  - {i}")

        add("Orchestrators", flows.get("orchestrators", []))
        add("Providers", flows.get("providers", []))
        add("Memory Engines", flows.get("memory", []))
        add("World Models", flows.get("world", []))
        add("Plugin Systems", flows.get("plugins", []))
        add("HTTP Orchestrators", flows.get("http_orchestrators", []))
        add("Training Modules", flows.get("training", []))
        add("Self-Heal Modules", flows.get("self_heal", []))
        add("Agents", flows.get("agents", []))
        add("Recovery Modules", flows.get("recovery", []))
        add("Ability Catalogs", flows.get("ability_catalogs", []))
        add("Multi-Agent Pipelines", flows.get("multi_agent", []))

        self.out.write_text("\n".join(lines), encoding="utf-8")
        return {"visualized": str(self.out)}
