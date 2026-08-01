"""
RealAI Auto-Discovering Plugin System
"""

import importlib
from pathlib import Path
from typing import List

def auto_load_plugins() -> List[str]:
    """Automatically discover and load all plugins."""
    plugins_dir = Path("plugins")
    loaded = []
    
    for item in plugins_dir.iterdir():
        if item.is_dir() and not item.name.startswith("__") and not item.name.startswith("."):
            try:
                importlib.import_module(f"plugins.{item.name}")
                loaded.append(item.name)
                print(f"✅ Loaded plugin module: {item.name}")
            except Exception as e:
                print(f"⚠️  Could not load {item.name}: {e}")
    
    return loaded

# Auto-load on import
loaded_plugins = auto_load_plugins()

print(f"✅ RealAI Plugin System Ready ({len(loaded_plugins)} modules loaded)")