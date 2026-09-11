#!/usr/bin/env python3
"""
RealAI Model Catalog Facade
===========================
Exposes RealAI model IDs to clients (realai-default-coder, realai-1.0-instruct, …)
while mapping to local GGUF paths for Vulkan llama-server.

Clients should only see RealAI IDs from GET /v1/models — not raw engine filenames.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_PKG = Path(__file__).resolve().parent
_ROOT = _PKG.parent
_SCAN = _ROOT / "scan_results"
_REGISTRY = _ROOT / "config" / "realai_models.json"

VULKAN_BASE = os.environ.get("REALAI_VULKAN_BASE", "http://127.0.0.1:8080").rstrip("/")


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_connect_candidates() -> List[Dict[str, Any]]:
    p = _SCAN / "weights_connect_candidates.json"
    cands: List[Dict[str, Any]] = []
    if p.is_file():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            cands = list(data.get("candidates") or [])
        except Exception:
            cands = []
    # Enrich from staged/runtime .realai/local_models.json if present
    for lp in (
        _ROOT / "recovered" / "from_users_dotfiles" / ".realai" / "local_models.json",
        Path(os.environ.get("USERPROFILE", r"C:\Users\tsmit")) / ".realai" / "local_models.json",
    ):
        if not lp.is_file():
            continue
        try:
            lm = json.loads(lp.read_text(encoding="utf-8"))
            for mid, meta in (lm.get("models") or {}).items():
                if not isinstance(meta, dict):
                    continue
                path = meta.get("path") or ""
                if not path or not str(path).lower().endswith(".gguf"):
                    continue
                # skip if already have same filename
                fn = Path(str(path)).name
                if any(str(c.get("name") or "").lower() == fn.lower() for c in cands):
                    continue
                cands.append({
                    "name": fn,
                    "path": path,
                    "size_gb": None,
                    "family": "realai" if "realai" in str(mid).lower() else "local",
                    "role": "gguf_chat" if meta.get("type") in (None, "llm", "chat") else meta.get("type"),
                    "is_live_default": str(mid) == str(lm.get("default_llm") or ""),
                    "is_realai_named": "realai" in str(mid).lower() or "realai" in fn.lower(),
                    "incomplete_copy": False,
                    "copies": [path],
                    "copy_count": 1,
                    "vulkan_cmd": (
                        f'llama-server.exe -m "{path}" --host 127.0.0.1 --port 8080 '
                        f"-c {meta.get('context_length') or 8192} -ngl 99 --jinja"
                    ),
                    "realai_model_id_suggestion": str(mid).replace("_", "-"),
                    "source": f"local_models.json:{lp}",
                })
        except Exception:
            continue
    return cands


def _load_registry_file() -> Dict[str, Any]:
    if _REGISTRY.is_file():
        try:
            return json.loads(_REGISTRY.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_registry(models: List[Dict[str, Any]]) -> Path:
    """Persist registry for stable IDs across restarts."""
    _REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": _utc(),
        "owned_by": "realai",
        "provider": "realai-v3",
        "models": models,
        "note": (
            "RealAI public model IDs. backend_filename is what llama-server currently "
            "expects when that GGUF is loaded. Only one GGUF is hot on :8080 at a time."
        ),
    }
    _REGISTRY.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return _REGISTRY


def vulkan_loaded_model_ids() -> List[str]:
    """What the engine currently has loaded (raw filenames/ids)."""
    try:
        with urllib.request.urlopen(f"{VULKAN_BASE}/v1/models", timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return []
    ids: List[str] = []
    # OpenAI shape
    for m in data.get("data") or []:
        if isinstance(m, dict) and m.get("id"):
            ids.append(str(m["id"]))
    # llama.cpp sometimes uses models[]
    for m in data.get("models") or []:
        if isinstance(m, dict):
            n = m.get("name") or m.get("model") or m.get("id")
            if n:
                ids.append(str(n))
        elif isinstance(m, str):
            ids.append(m)
    # dedupe preserve
    seen = set()
    out = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _suggest_id(c: Dict[str, Any]) -> str:
    name = str(c.get("name") or "model")
    nl = name.lower()
    # Prefer specific RealAI / size-aware ids over generic scanner suggestions
    if c.get("is_live_default") or ("qwen" in nl and "coder" in nl and not c.get("incomplete_copy")):
        return "realai-default-coder"
    if "realai" in nl and "1.0" in nl:
        return "realai-1.0-instruct"
    if "realai" in nl and "overseer" in nl:
        return "realai-overseer"
    if "3b" in nl:
        return "local-llama-3b"
    if "1b" in nl:
        return "local-llama-1b"
    if "7b" in nl and "qwen" in nl:
        return "local-qwen-7b"
    sug = c.get("realai_model_id_suggestion")
    if sug and str(sug) not in ("local-llama", "local-qwen", "local-model"):
        return str(sug)
    fam = c.get("family") or "model"
    return f"local-{fam}"


def _is_same_file(a: str, b: str) -> bool:
    """Loose match between vulkan id and gguf path/name."""
    al = a.replace("\\", "/").lower()
    bl = b.replace("\\", "/").lower()
    an = Path(a).name.lower()
    bn = Path(b).name.lower()
    return an == bn or an in bl or bn in al or al == bl


def build_catalog(include_incomplete: bool = False) -> Dict[str, Any]:
    """Build OpenAI-compatible models list with RealAI IDs."""
    candidates = _load_connect_candidates()
    loaded = vulkan_loaded_model_ids()
    loaded_set = loaded

    models: List[Dict[str, Any]] = []
    used_ids: set = set()

    for c in candidates:
        if c.get("incomplete_copy") and not include_incomplete:
            continue
        mid = _suggest_id(c)
        # uniquify
        base = mid
        n = 2
        while mid in used_ids:
            mid = f"{base}-{n}"
            n += 1
        used_ids.add(mid)

        path = str(c.get("path") or "")
        name = str(c.get("name") or "")
        # Is this the currently loaded backend weight?
        live = False
        for lid in loaded_set:
            if _is_same_file(lid, name) or _is_same_file(lid, path):
                live = True
                break
        if c.get("is_live_default") and not loaded_set:
            # assume default if engine down
            live = True

        entry = {
            "id": mid,
            "object": "model",
            "created": int(datetime.now(timezone.utc).timestamp()),
            "owned_by": "realai",
            "permission": [],
            "root": mid,
            "parent": None,
            # RealAI extensions
            "realai": {
                "display_name": mid,
                "family": c.get("family") or "local",
                "role": c.get("role") or "gguf_chat",
                "gguf_path": path,
                "gguf_filename": name,
                "size_gb": c.get("size_gb"),
                "backend": "llama.cpp-vulkan",
                "backend_model_id": name,  # what to send to :8080 when this GGUF is loaded
                "loaded_now": live,
                "copy_count": c.get("copy_count") or 1,
                "is_realai_named": bool(c.get("is_realai_named")),
                "incomplete_copy": bool(c.get("incomplete_copy")),
                "capabilities": ["chat", "completion"] + (
                    ["coding"] if "coder" in name.lower() or "coder" in mid else []
                ),
                "switch_cmd": c.get("vulkan_cmd"),
            },
        }
        models.append(entry)

    # Ensure at least default if empty
    if not models:
        models.append({
            "id": "realai-default",
            "object": "model",
            "created": int(datetime.now(timezone.utc).timestamp()),
            "owned_by": "realai",
            "realai": {
                "display_name": "realai-default",
                "gguf_filename": os.environ.get(
                    "REALAI_DEFAULT_MODEL", "qwen2.5-coder-7b-instruct-q5_k_m.gguf"
                ),
                "backend": "llama.cpp-vulkan",
                "loaded_now": True,
                "capabilities": ["chat", "completion"],
            },
        })

    # Always expose local embeddings facade id
    if "realai-embeddings" not in used_ids:
        models.append({
            "id": "realai-embeddings",
            "object": "model",
            "created": int(datetime.now(timezone.utc).timestamp()),
            "owned_by": "realai",
            "permission": [],
            "root": "realai-embeddings",
            "parent": None,
            "realai": {
                "display_name": "realai-embeddings",
                "family": "embeddings",
                "role": "embeddings",
                "backend": "realai-local-deterministic",
                "loaded_now": True,
                "capabilities": ["embeddings"],
                "endpoint": "POST /v1/embeddings",
                "source": "lambda_embeddings_audio + server.embeddings_backend",
            },
        })
        used_ids.add("realai-embeddings")

    # Recovered LoRA adapters (not Vulkan-loaded; cataloged for finetune / ability)
    try:
        from realai.recovery_registry import list_lora_adapters
        for ad in list_lora_adapters(limit=40):
            mid = ad.get("id") or f"realai-lora-{ad.get('name')}"
            if mid in used_ids:
                continue
            used_ids.add(mid)
            models.append({
                "id": mid,
                "object": "model",
                "created": int(datetime.now(timezone.utc).timestamp()),
                "owned_by": "realai",
                "permission": [],
                "root": mid,
                "parent": ad.get("base_model_name_or_path"),
                "realai": {
                    "display_name": mid,
                    "family": "lora",
                    "role": "lora_adapter",
                    "adapter_path": ad.get("path"),
                    "has_weights": ad.get("has_weights"),
                    "weights_bytes": ad.get("weights_bytes"),
                    "base_model": ad.get("base_model_name_or_path"),
                    "peft_r": ad.get("r"),
                    "backend": "peft-lora",
                    "loaded_now": False,
                    "capabilities": ["finetune", "lora"],
                    "source": "checkpoints_lora (realai2 recovery)",
                },
            })
    except Exception:
        pass

    # Aliases for convenience
    aliases = {
        "realai-default": "realai-default-coder",
        "realai": "realai-default-coder",
        "default": "realai-default-coder",
    }
    # only keep aliases that point to existing
    id_set = {m["id"] for m in models}
    aliases = {k: v for k, v in aliases.items() if v in id_set}

    # Prefer loaded model as default
    default_id = None
    for m in models:
        if (m.get("realai") or {}).get("loaded_now"):
            default_id = m["id"]
            break
    if not default_id and models:
        default_id = models[0]["id"]

    catalog = {
        "object": "list",
        "data": models,
        "realai": {
            "provider": "realai-v3",
            "default_model": default_id,
            "aliases": aliases,
            "vulkan_base": VULKAN_BASE,
            "vulkan_loaded_raw": loaded,
            "weights_scan": str(_SCAN / "weights_connect_candidates.json"),
            "registry_file": str(_REGISTRY),
            "note": (
                "Public IDs are RealAI-owned. Only one GGUF is active on Vulkan at a time; "
                "models with loaded_now=false need a server restart with switch_cmd."
            ),
        },
    }

    # persist slim registry
    try:
        save_registry([
            {
                "id": m["id"],
                "gguf_path": (m.get("realai") or {}).get("gguf_path"),
                "gguf_filename": (m.get("realai") or {}).get("gguf_filename"),
                "family": (m.get("realai") or {}).get("family"),
                "loaded_now": (m.get("realai") or {}).get("loaded_now"),
            }
            for m in models
        ])
    except Exception:
        pass

    return catalog


def resolve_model_for_backend(requested: Optional[str]) -> Tuple[str, Dict[str, Any]]:
    """
    Map client model id → backend filename for Vulkan + meta.

    Returns (backend_model_id, meta_dict).
    If requested model is not currently loaded, still map to backend filename
    of requested id but set loaded_now=False and use currently loaded backend
    for the actual request (so chat doesn't 404).
    """
    catalog = build_catalog()
    models = catalog.get("data") or []
    aliases = (catalog.get("realai") or {}).get("aliases") or {}
    default_id = (catalog.get("realai") or {}).get("default_model")
    loaded_raw = (catalog.get("realai") or {}).get("vulkan_loaded_raw") or []

    req = (requested or "").strip() or default_id or "realai-default-coder"
    req = aliases.get(req, req)

    by_id = {m["id"]: m for m in models if isinstance(m, dict)}
    # also allow raw gguf name
    by_file = {}
    for m in models:
        fn = (m.get("realai") or {}).get("gguf_filename")
        if fn:
            by_file[str(fn).lower()] = m
            by_file[str(fn).lower().replace(".gguf", "")] = m

    entry = by_id.get(req) or by_file.get(req.lower())
    if not entry:
        # unknown — pass through to backend as-is
        backend = req
        if loaded_raw:
            backend = loaded_raw[0]
        return backend, {
            "requested": requested,
            "resolved_id": req,
            "backend_model_id": backend,
            "loaded_now": True,
            "unknown_model": True,
            "owned_by": "realai",
        }

    rmeta = entry.get("realai") or {}
    backend_file = rmeta.get("gguf_filename") or req
    loaded_now = bool(rmeta.get("loaded_now"))

    # Actual request to vulkan must use currently loaded model id
    if loaded_raw:
        actual_backend = loaded_raw[0]
    else:
        actual_backend = backend_file

    return actual_backend, {
        "requested": requested,
        "resolved_id": entry["id"],
        "display_name": entry["id"],
        "gguf_path": rmeta.get("gguf_path"),
        "gguf_filename": backend_file,
        "backend_model_id": actual_backend,
        "loaded_now": loaded_now,
        "switch_required": not loaded_now,
        "switch_cmd": rmeta.get("switch_cmd"),
        "owned_by": "realai",
        "family": rmeta.get("family"),
        "note": (
            None if loaded_now else
            f"Model {entry['id']} is registered but not loaded on Vulkan; "
            f"serving currently loaded backend {actual_backend}. Restart Vulkan with switch_cmd to activate."
        ),
    }


def openai_models_payload() -> Dict[str, Any]:
    """Payload for GET /v1/models — OpenAI compatible + realai block."""
    cat = build_catalog()
    # OpenAI clients only need data[].id — keep realai block for RealAI clients
    return cat
