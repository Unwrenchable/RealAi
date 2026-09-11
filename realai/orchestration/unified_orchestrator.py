import json
from pathlib import Path

class UnifiedOrchestrator:
    """
    Builds a unified orchestrator based on scan results.
    """

    def __init__(self, root: Path, scan_manifest: Path):
        self.root = root
        self.scan_manifest = scan_manifest

    def build(self):
        data = json.loads(self.scan_manifest.read_text(encoding="utf-8"))
        flows = data.get("flows", {})

        orchestrators = flows.get("orchestrators", [])
        providers = flows.get("providers", [])
        memory = flows.get("memory", [])
        world = flows.get("world", [])
        plugins = flows.get("plugins", [])

        return {
            "orchestrators": orchestrators,
            "provider": providers[0] if providers else None,
            "memory": memory[0] if memory else None,
            "world": world[0] if world else None,
            "plugins": plugins,
            "note": "This is the unified orchestrator blueprint. You can now assemble it manually."
        }
