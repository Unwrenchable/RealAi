"""Model registry backed by models.yaml."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config.loader import Config

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def _coerce_models(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, dict):
        if "models" in raw and isinstance(raw["models"], list):
            return [item for item in raw["models"] if isinstance(item, dict)]
        output = []
        for model_id, cfg in raw.items():
            if isinstance(cfg, dict):
                item = dict(cfg)
                item.setdefault("id", model_id)
                output.append(item)
        return output
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


class ModelRegistry:
    """Load model metadata from a YAML registry file."""

    def __init__(self, path: Optional[str] = None):
        cfg = Config()
        path = path or cfg.paths.models
        self.path = Path(path)
        if not self.path.exists():
            self.data = {"models": []}
            return
        text = self.path.read_text(encoding="utf-8")
        if yaml is not None:
            parsed = yaml.safe_load(text) or {}
        else:
            parsed = _parse_yaml_fallback(text)
        self.data = parsed if isinstance(parsed, dict) else {"models": []}

    def list_models(self):
        return _coerce_models(self.data)


def _parse_yaml_fallback(text: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    current_key = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if not raw_line.startswith(" ") and ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value:
                data[key] = value
                current_key = None
            else:
                data[key] = {}
                current_key = key
        elif current_key and ":" in line and isinstance(data.get(current_key), dict):
            sub_key, _, sub_value = line.partition(":")
            data[current_key][sub_key.strip()] = sub_value.strip()
    return data
