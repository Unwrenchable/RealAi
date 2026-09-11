"""In-memory model cache for registry and runtime loaders."""

from typing import Any, Callable, Dict


class ModelCache:
    def __init__(self):
        self.loaded: Dict[str, Any] = {}

    def get(self, model_id: str, loader: Callable[[], Any]):
        if model_id not in self.loaded:
            self.loaded[model_id] = loader()
        return self.loaded[model_id]

    def clear(self):
        self.loaded.clear()

