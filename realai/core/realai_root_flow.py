import ast
import json
from pathlib import Path
from typing import Any, Dict, List

def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except:
        return ""

def safe_write(path: Path, obj: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

class RealAIRootFlow:
    """
    Walks the entire RealAI-clean root and reconstructs the intended architecture.
    """

    def __init__(self, root: Path, out: Path):
        self.root = root
        self.out = out

    def run(self):
        modules = self._scan_all()
        flows = self._infer_flows(modules)
        manifest = {
            "root": str(self.root),
            "modules": modules,
            "flows": flows,
            "intended_architecture": self._architecture(flows),
        }
        safe_write(self.out, manifest)

    def _scan_all(self) -> List[Dict[str, Any]]:
        modules = []
        for py in self.root.rglob("*.py"):
            rel = py.relative_to(self.root)
            text = safe_read(py)
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue

            classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            calls = []
            for n in ast.walk(tree):
                if isinstance(n, ast.Call):
                    try:
                        calls.append(ast.unparse(n.func))
                    except:
                        pass

            modules.append({
                "path": str(rel),
                "classes": classes,
                "functions": funcs,
                "calls": calls,
            })
        return modules

    def _infer_flows(self, modules):
        flows = {
            "orchestrators": [],
            "providers": [],
            "memory": [],
            "world": [],
            "plugins": [],
            "http_orchestrators": [],
            "training": [],
            "self_heal": [],
            "agents": [],
            "runtime_bridges": [],
            "recovery": [],
            "ability_catalogs": [],
            "multi_agent": [],
        }

        for m in modules:
            path = m["path"]
            classes = m["classes"]
            calls = m["calls"]

            if any("Orchestrator" in c for c in classes):
                flows["orchestrators"].append(path)

            if any("Provider" in c or "SelfHealingProvider" in c for c in classes):
                flows["providers"].append(path)

            if any("MemoryEngine" in c or "Memory" in c for c in classes):
                flows["memory"].append(path)

            if any("WorldModel" in c for c in classes):
                flows["world"].append(path)

            if any("PluginSystem" in c or "PluginExecutor" in c for c in classes):
                flows["plugins"].append(path)

            if "BaseHTTPRequestHandler" in calls or "ThreadingHTTPServer" in calls:
                flows["http_orchestrators"].append(path)

            if any("FineTune" in c or "Trainer" in c for c in classes):
                flows["training"].append(path)

            if "self_heal" in path.lower():
                flows["self_heal"].append(path)

            if "agent" in path.lower():
                flows["agents"].append(path)

            if "runtime_bridge" in path.lower():
                flows["runtime_bridges"].append(path)

            if "recovery" in path.lower():
                flows["recovery"].append(path)

            if "ability" in path.lower():
                flows["ability_catalogs"].append(path)

            if "multi_agent" in path.lower():
                flows["multi_agent"].append(path)

        return flows

    def _architecture(self, flows):
        return {
            "core": {
                "orchestrators": flows["orchestrators"],
                "providers": flows["providers"],
                "memory": flows["memory"],
                "world": flows["world"],
                "plugins": flows["plugins"],
            },
            "external_api": {
                "http_orchestrators": flows["http_orchestrators"],
                "runtime_bridges": flows["runtime_bridges"],
            },
            "training": flows["training"],
            "self_heal": flows["self_heal"],
            "agents": flows["agents"],
            "recovery": flows["recovery"],
            "ability_catalogs": flows["ability_catalogs"],
            "multi_agent": flows["multi_agent"],
            "summary": "This is the reconstructed RealAI architecture based on all modules found under the root.",
        }
