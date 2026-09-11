import json
from pathlib import Path

class RealAIRetirement:
    """
    Flags obsolete modules: not referenced by orchestrators, providers,
    memory engines, world models, plugins, or HTTP orchestrators.
    """

    def __init__(self, root: Path, scan_manifest: Path, out: Path):
        self.root = root
        self.scan_manifest = scan_manifest
        self.out = out

    def run(self):
        data = json.loads(self.scan_manifest.read_text(encoding="utf-8"))
        modules = {m["path"] for m in data.get("modules", [])}

        flows = data.get("flows", {})
        used = set(
            flows.get("orchestrators", []) +
            flows.get("providers", []) +
            flows.get("memory", []) +
            flows.get("world", []) +
            flows.get("plugins", []) +
            flows.get("http_orchestrators", []) +
            flows.get("training", []) +
            flows.get("self_heal", []) +
            flows.get("agents", []) +
            flows.get("runtime_bridges", []) +
            flows.get("recovery", []) +
            flows.get("ability_catalogs", []) +
            flows.get("multi_agent", [])
        )

        obsolete = sorted(modules - used)

        self.out.write_text(json.dumps({"obsolete": obsolete}, indent=2))
        return {"obsolete": obsolete}
