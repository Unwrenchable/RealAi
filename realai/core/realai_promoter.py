import shutil
from pathlib import Path
import json

class RealAIPromoter:
    """
    Promotes canonical modules (from scan manifest) into core/.
    """

    def __init__(self, root: Path, scan_manifest: Path, core_dir: Path):
        self.root = root
        self.scan_manifest = scan_manifest
        self.core_dir = core_dir

    def run(self):
        data = json.loads(self.scan_manifest.read_text(encoding="utf-8"))
        flows = data.get("flows", {})
        promoted = []

        canonical = (
            flows.get("orchestrators", []) +
            flows.get("providers", []) +
            flows.get("memory", []) +
            flows.get("world", []) +
            flows.get("plugins", [])
        )

        for rel in canonical:
            src = self.root / rel
            dst = self.core_dir / src.name
            if src.exists():
                shutil.copy2(src, dst)
                promoted.append(str(dst))

        return {"promoted": promoted}
