"""Apply [native] settings from realai.toml so owned models can load without F16/HF."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from ..model_assets import resolve_realai_gguf

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[2]


def _load_native_section() -> Dict[str, Any]:
    try:
        import tomllib
    except ImportError:
        return {}
    path = _ROOT / "realai.toml"
    if not path.is_file():
        return {}
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    native = data.get("native")
    return native if isinstance(native, dict) else {}


def apply_native_bootstrap(model_id: str | None = None) -> Dict[str, Any]:
    native = _load_native_section()
    if not native.get("auto_bootstrap"):
        return {"status": "disabled"}

    from ..training.bootstrap_weights import bootstrap_native_weights

    mid = model_id or native.get("model_id")
    if not mid:
        from .config import load_settings

        mid = load_settings().default_chat_model

    existing, _ = resolve_realai_gguf(str(mid))
    if existing is not None:
        return {"status": "already_ready", "model_id": mid, "gguf": str(existing)}

    source = native.get("bootstrap_gguf")
    logger.info("Bootstrapping native weights for %s from %s", mid, source)
    return bootstrap_native_weights(model_id=str(mid), source=str(source) if source else None)