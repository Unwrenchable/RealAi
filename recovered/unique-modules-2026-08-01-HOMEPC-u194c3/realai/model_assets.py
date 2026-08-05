"""Resolve on-disk GGUF assets for RealAI-owned model IDs.

RealAI chat models must load weights from the repo (or REALAI_WEIGHTS_ROOT),
not from third-party API providers or disguised base-model paths.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MODELS_ROOT = _REPO_ROOT / "models"


def repo_root() -> Path:
    return _REPO_ROOT


def models_root() -> Path:
    env = os.environ.get("REALAI_WEIGHTS_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return _MODELS_ROOT


_NON_GGUF_REALAI_IDS = frozenset({"realai-embed", "realai-vision"})


def is_realai_owned_model(model_id: str, cfg: Optional[Dict[str, Any]] = None) -> bool:
    mid = (model_id or "").strip().lower()
    if mid in _NON_GGUF_REALAI_IDS:
        return False
    if cfg and str(cfg.get("owned_by", "")).lower() == "realai":
        return mid.startswith("realai-")
    return mid.startswith("realai-")


def _read_manifest(model_id: str) -> Dict[str, Any]:
    manifest_path = models_root() / model_id / "manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _gguf_candidates_in_dir(directory: Path) -> List[Path]:
    if not directory.is_dir():
        return []
    files = sorted(directory.glob("*.gguf"))
    return [p for p in files if p.is_file()]


def _resolve_configured_path(raw_path: str) -> Optional[Path]:
    if not raw_path or not str(raw_path).strip():
        return None
    text = str(raw_path).strip()
    candidate = Path(text).expanduser()
    if candidate.is_absolute():
        return candidate if candidate.is_file() else None
    for base in (repo_root(), models_root(), Path.cwd()):
        joined = (base / candidate).resolve()
        if joined.is_file():
            return joined
    return None


def resolve_realai_gguf(
    model_id: str,
    configured_path: Optional[str] = None,
) -> Tuple[Optional[Path], Dict[str, Any]]:
    """Return (gguf_path, diagnostics) for a RealAI-owned model."""
    diagnostics: Dict[str, Any] = {
        "model_id": model_id,
        "weights_root": str(models_root()),
        "status": "missing",
    }
    manifest = _read_manifest(model_id)
    diagnostics["manifest"] = manifest.get("name", model_id)

    for key in ("gguf", "weights_file", "gguf_path"):
        manifest_path = manifest.get(key)
        if manifest_path:
            resolved = _resolve_configured_path(str(manifest_path))
            if resolved and resolved.suffix.lower() == ".gguf":
                diagnostics.update({"status": "ready", "source": f"manifest.{key}"})
                return resolved, diagnostics

    if configured_path:
        hint = str(configured_path).strip()
        if hint.endswith(".gguf"):
            resolved = _resolve_configured_path(hint)
            if resolved:
                diagnostics.update({"status": "ready", "source": "registry.path"})
                return resolved, diagnostics

    model_dir = models_root() / model_id
    for sub in ("weights", ""):
        search_dir = model_dir / sub if sub else model_dir
        candidates = _gguf_candidates_in_dir(search_dir)
        if candidates:
            preferred = manifest.get("preferred_gguf")
            if preferred:
                for path in candidates:
                    if path.name == preferred:
                        diagnostics.update({"status": "ready", "source": "weights.preferred"})
                        return path, diagnostics
            diagnostics.update(
                {
                    "status": "ready",
                    "source": "weights.auto",
                    "candidates": [p.name for p in candidates],
                }
            )
            return candidates[0], diagnostics

    diagnostics["expected_paths"] = [
        str(model_dir / "weights" / "<name>.gguf"),
        str(model_dir / "<name>.gguf"),
    ]
    return None, diagnostics


def resolve_inference_gguf_path(
    model_id: str,
    cfg: Dict[str, Any],
) -> Tuple[str, Dict[str, Any]]:
    """Normalize registry config to an absolute GGUF path when applicable."""
    backend = str(cfg.get("backend", "")).lower()
    raw_path = str(cfg.get("path", model_id))
    meta = dict(cfg)

    if backend in ("realai-gguf", "realai-native"):
        gguf, diag = resolve_realai_gguf(model_id, raw_path)
        meta["weight_diagnostics"] = diag
        if gguf:
            meta["resolved_gguf"] = str(gguf)
            return str(gguf), meta
        raise FileNotFoundError(
            "RealAI model '{0}' has no GGUF weights on disk. {1}".format(
                model_id,
                "Expected: {0}".format(", ".join(diag.get("expected_paths", []))),
            )
        )

    if is_realai_owned_model(model_id, cfg) and backend in (
        "llama-cli",
        "llama.cpp",
        "llamacpp",
        "llamacli",
    ):
        if raw_path.endswith(".gguf"):
            resolved = _resolve_configured_path(raw_path)
            if resolved:
                meta["resolved_gguf"] = str(resolved)
                return str(resolved), meta
        gguf, diag = resolve_realai_gguf(model_id, raw_path)
        meta["weight_diagnostics"] = diag
        if gguf:
            meta["resolved_gguf"] = str(gguf)
            return str(gguf), meta
        raise FileNotFoundError(
            "RealAI model '{0}' requires GGUF weights under models/{0}/weights/. {1}".format(
                model_id,
                diag,
            )
        )

    resolved = _resolve_configured_path(raw_path)
    if resolved and resolved.suffix.lower() == ".gguf":
        meta["resolved_gguf"] = str(resolved)
        return str(resolved), meta
    return raw_path, meta


def list_realai_weight_status() -> List[Dict[str, Any]]:
    """Summarize which RealAI-owned chat models have loadable GGUF files."""
    rows: List[Dict[str, Any]] = []
    root = models_root()
    if not root.exists():
        return rows
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        model_id = entry.name
        if not is_realai_owned_model(model_id):
            continue
        gguf, diag = resolve_realai_gguf(model_id)
        rows.append(
            {
                "model_id": model_id,
                "ready": gguf is not None,
                "gguf": str(gguf) if gguf else None,
                "diagnostics": diag,
            }
        )
    return rows