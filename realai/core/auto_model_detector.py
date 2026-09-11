import json
from pathlib import Path

class AutoModelDetector:
    """
    Scans a model directory for GGUF files, extracts metadata, classifies models,
    and builds a clean RealAI model registry automatically.
    """

    def __init__(self, model_root: Path, out_path: Path):
        self.model_root = model_root
        self.out_path = out_path

    def run(self):
        models = self._scan_models()
        registry = self._build_registry(models)
        self._write_registry(registry)
        return registry

    def _scan_models(self):
        ggufs = []
        for p in self.model_root.rglob("*.gguf"):
            ggufs.append(p)
        return ggufs

    def _classify(self, path: Path):
        name = path.name.lower()

        if "qwen" in name:
            return "qwen"
        if "realai" in name:
            return "realai"
        if "llama" in name:
            return "llama"
        return "unknown"

    def _build_registry(self, ggufs):
        registry = {}

        for p in ggufs:
            model_type = self._classify(p)
            model_id = p.stem.replace(".", "-").replace("_", "-")

            entry = {
                "type": "chat",
                "backend": "llama.cpp-vulkan",
                "path": str(p),
                "context_length": self._infer_context(p),
                "owned_by": "realai" if model_type in ("realai", "qwen") else "local",
                "capabilities": self._infer_capabilities(model_type),
            }

            registry[model_id] = entry

        return registry

    def _infer_context(self, path: Path):
        name = path.name.lower()
        if "7b" in name or "coder" in name:
            return 8192
        if "1b" in name:
            return 4096
        return 4096

    def _infer_capabilities(self, model_type: str):
        if model_type == "qwen":
            return ["chat", "completion", "coding"]
        if model_type == "realai":
            return ["chat", "completion"]
        if model_type == "llama":
            return ["chat", "completion"]
        return ["chat"]

    def _write_registry(self, registry):
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        self.out_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
