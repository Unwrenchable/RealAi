import json
import ast
from pathlib import Path

def safe_read_text(path: Path):
    try:
        return path.read_text(encoding="utf-8")
    except:
        return ""

def safe_write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

class RepoEngineer:
    def __init__(self, repo_root: Path, plugins_root: Path, manifest_path: Path):
        self.repo_root = repo_root          # C:\RealAI-clean
        self.plugins_root = plugins_root    # C:\models\checkpoints_lora\plugins
        self.manifest_path = manifest_path  # C:\models\checkpoints_lora\realai_repo_manifest.json

    def run_cycle(self):
        scan = self.scan_repo()
        self.generate_plugins_from_repo(scan)
        self.generate_plugins_from_lora()
        self.fix_import_collisions(scan)
        self.update_manifest(scan)

    # ---------- SCAN ----------

    def scan_repo(self):
        modules = []
        for py in self.repo_root.rglob("*.py"):
            rel = py.relative_to(self.repo_root)
            text = safe_read_text(py)
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue

            classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            todos = [l.strip() for l in text.splitlines() if "TODO" in l]

            modules.append({
                "path": str(rel),
                "classes": classes,
                "functions": funcs,
                "todos": todos,
            })

        return {"modules": modules}

    # ---------- PLUGIN GENERATION FROM REPO ----------

    def generate_plugins_from_repo(self, scan):
        modules = scan["modules"]
        new_plugins = []

        for m in modules:
            path = m["path"]
            classes = m["classes"]
            todos = m["todos"]

            # Example: generate plugins for agent-like classes
            for cls in classes:
                if "Agent" in cls or "Engineer" in cls or "Coordinator" in cls:
                    plugin_name = cls.replace(" ", "-").lower()
                    plugin_file = self.plugins_root / f"{plugin_name}.json"
                    if not plugin_file.exists():
                        new_plugins.append((plugin_file, {
                            "name": plugin_name,
                            "type": "agent",
                            "description": f"Auto-generated agent plugin for {cls} from {path}.",
                            "schedule": "continuous"
                        }))

            # Example: generate plugins from TODO markers
            for todo in todos:
                if "plugin" in todo.lower():
                    plugin_name = "todo-plugin-" + str(abs(hash(todo)))[:8]
                    plugin_file = self.plugins_root / f"{plugin_name}.json"
                    if not plugin_file.exists():
                        new_plugins.append((plugin_file, {
                            "name": plugin_name,
                            "type": "system",
                            "description": f"Auto-generated from TODO: {todo}",
                            "schedule": "manual"
                        }))

        for pf, obj in new_plugins:
            safe_write_json(pf, obj)

    # ---------- PLUGIN GENERATION FROM LORA ----------

    def generate_plugins_from_lora(self):
        # Map LoRA adapter directories to plugins
        lora_root = self.plugins_root.parent  # C:\models\checkpoints_lora
        for d in lora_root.iterdir():
            if not d.is_dir():
                continue
            adapter = d / "adapter_model.safetensors"
            if not adapter.exists():
                continue

            plugin_name = d.name
            plugin_file = self.plugins_root / f"{plugin_name}.json"
            if plugin_file.exists():
                continue

            safe_write_json(plugin_file, {
                "name": plugin_name,
                "type": "agent",
                "description": f"Auto-generated plugin for LoRA adapter {d.name}.",
                "schedule": "continuous"
            })

    # ---------- REPO FIXES ----------

    def fix_import_collisions(self, scan):
        # Simple heuristic: detect folders shadowing .py files with same name
        collisions = []
        for m in scan["modules"]:
            path = Path(m["path"])
            if path.name == "__init__.py":
                continue
            stem = path.stem
            folder = self.repo_root / stem
            file = self.repo_root / path
            if folder.exists() and file.exists():
                collisions.append((folder, file))

        # For now, just log; you can extend to auto-rename
        if collisions:
            report = {
                "import_collisions": [
                    {"folder": str(f), "file": str(fi)} for f, fi in collisions
                ]
            }
            safe_write_json(self.repo_root / "repo_import_collisions.json", report)

    # ---------- MANIFEST UPDATE ----------

    def update_manifest(self, scan):
        modules = scan["modules"]
        manifest = {
            "modules": modules,
            "plugins": self._list_plugins(),
        }
        safe_write_json(self.manifest_path, manifest)

    def _list_plugins(self):
        plugins = []
        if not self.plugins_root.exists():
            return plugins
        for p in self.plugins_root.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except:
                continue
            data["__path"] = str(p)
            plugins.append(data)
        return plugins
