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
# Canonical weights live outside the nested/archive-heavy repo tree
_MODELS_DIR = Path(
    os.environ.get("REALAI_MODELS_DIR", r"C:\models\checkpoints_lora")
)
_REPO_MODELS_DIR = _ROOT / "models"
_MODELS_SEARCH_DIRS = [
    _MODELS_DIR,
    Path(r"C:\models"),
    Path(r"C:\models\checkpoints_lora"),
    _REPO_MODELS_DIR,
]

VULKAN_BASE = os.environ.get("REALAI_VULKAN_BASE", "http://127.0.0.1:8080").rstrip("/")


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_existing_gguf(name_or_path: str) -> Optional[Path]:
    """Prefer C:\\models\\checkpoints_lora over repo/nested copies."""
    raw = Path(str(name_or_path))
    if raw.is_file():
        return raw
    name = raw.name
    seen = set()
    for d in _MODELS_SEARCH_DIRS:
        try:
            key = str(d.resolve()) if d.exists() else str(d)
        except Exception:
            key = str(d)
        if key in seen:
            continue
        seen.add(key)
        cand = d / name
        if cand.is_file():
            return cand
    return None


def _normalize_path(p: Optional[str]) -> str:
    """Map WSL /mnt/c/... paths; resolve missing paths via checkpoints_lora first."""
    if not p:
        return ""
    s = str(p).strip().replace("\\", "/")
    # /mnt/c/Foo -> C:/Foo (Windows) or keep under WSL
    if s.lower().startswith("/mnt/") and len(s) > 6 and s[5].isalpha() and s[6] == "/":
        drive = s[5].upper()
        rest = s[7:]
        if os.name == "nt":
            s = f"{drive}:/{rest}"
        # else leave as /mnt/... for WSL Python
    try:
        candidate = Path(s)
        if candidate.is_file():
            out = str(candidate)
        else:
            found = _resolve_existing_gguf(s)
            out = str(found) if found else s
    except Exception:
        out = s
    if os.name == "nt" and ":" in out[:3]:
        return out.replace("/", "\\")
    return out


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
    text = json.dumps(payload, indent=2)
    # Package registry (canonical for model_catalog) + product-root twin.
    targets = [_REGISTRY, _ROOT.parent / "config" / "realai_models.json"]
    written = _REGISTRY
    for target in targets:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            written = target
        except Exception:
            continue
    return written


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


# Stable public IDs keyed by exact GGUF basename under C:\models\checkpoints_lora
_FILENAME_TO_ID = {
    "qwen2.5-coder-7b-instruct-q5_k_m.gguf": "realai-default-coder",
    "qwen2.5-coder-1.5b-instruct-q5_k_m.gguf": "realai-coder-1.5b",
    "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf": "realai-coder-1.5b-q4",
    "qwen2.5-coder-1.5b-instruct-q4_0.gguf": "realai-coder-1.5b-q4_0",
    "qwen2.5-coder-1.5b-instruct-q5_0.gguf": "realai-coder-1.5b-q5_0",
    "qwen2.5-coder-1.5b-instruct-q6_k.gguf": "realai-coder-1.5b-q6",
    "qwen2.5-coder-1.5b-instruct-q8_0.gguf": "realai-coder-1.5b-q8",
    "qwen2.5-coder-1.5b-instruct-q3_k_m.gguf": "realai-coder-1.5b-q3",
    "qwen2.5-coder-1.5b-instruct-q2_k.gguf": "realai-coder-1.5b-q2",
    "realai-1.0-instruct-q4_k_m.gguf": "realai-1.0-instruct",
    "llama-3.2-1b-instruct-q4_k_m.gguf": "local-llama-1b",
    "llama-3.2-1b.gguf": "local-llama-1b-base",
    "llama-local-1b-q4_k_m.gguf": "local-llama-1b-alt",
    "qwen2.5-1.5b-lora-realai-q5_k_m.gguf": "realai-lora-1.5b",
    "qwen3.8-27b-q4_k_m.gguf": "local-qwen3-27b",
}


def _suggest_id(c: Dict[str, Any]) -> str:
    name = str(c.get("name") or "model")
    nl = name.lower()
    path = str(c.get("path") or "").replace("\\", "/").lower()
    blob = f"{nl} {path}"

    # Exact filename wins (prevents realai-default-coder-2..N spam)
    for key, mid in _FILENAME_TO_ID.items():
        if nl == key or nl.endswith("/" + key) or nl.endswith("\\" + key):
            return mid
        if Path(nl).name == key:
            return mid

    # Skip backup weights from public catalog ids
    if ".bak" in nl or nl.endswith(".bak.gguf"):
        return "local-backup-" + re.sub(r"[^a-z0-9]+", "-", Path(nl).stem)[:40].strip("-")

    # Canonical public IDs by GGUF content hints
    if "qwen" in blob and "coder" in blob and "7b" in blob and ".bak" not in blob:
        return "realai-default-coder"
    if "qwen" in blob and "coder" in blob and "1.5b" in blob and ".bak" not in blob:
        return "realai-coder-1.5b"
    if "realai" in blob and "1.0" in blob and "instruct" in blob:
        return "realai-1.0-instruct"
    if "realai" in blob and "overseer" in blob:
        return "realai-overseer"
    if "llama-3.2-1b" in blob or "llama-local-1b" in blob:
        return "local-llama-1b"
    if "qwen3.8-27b" in blob or ("qwen3" in blob and "27b" in blob):
        return "local-qwen3-27b"
    if "qwen2.5-1.5b-lora-realai" in blob:
        return "realai-lora-1.5b"
    if c.get("is_live_default"):
        return "realai-default-coder"
    if "3b" in nl and "llama" in blob:
        return "local-llama-3b"
    if "1b" in nl and "llama" in blob:
        return "local-llama-1b"

    sug = c.get("realai_model_id_suggestion")
    if sug and str(sug) not in (
        "local-llama",
        "local-qwen",
        "local-model",
        "qwen-coder-7b",
        "llama-local",
        "realai-1.0",  # prefer realai-1.0-instruct when file is instruct GGUF
        "realai-default-coder",  # only via exact 7B filename
    ):
        return str(sug)
    fam = c.get("family") or "model"
    stem = re.sub(r"[^a-z0-9]+", "-", Path(nl).stem.lower()).strip("-")[:48]
    return f"local-{stem or fam}"


def _is_same_file(a: str, b: str) -> bool:
    """Loose match between vulkan id and gguf path/name."""
    al = a.replace("\\", "/").lower()
    bl = b.replace("\\", "/").lower()
    an = Path(a).name.lower()
    bn = Path(b).name.lower()
    return an == bn or an in bl or bn in al or al == bl


def _iter_ggufs(models_dir: Path) -> List[Path]:
    """List usable GGUFs under checkpoints_lora (skip backups / mmproj / quarantine)."""
    if not models_dir.is_dir():
        return []
    out: List[Path] = []
    # Recursive: nested packs like Qwen3-30B-A3B/qwen3.8-27b/*.gguf
    for gguf in sorted(models_dir.rglob("*.gguf")):
        nl = gguf.name.lower()
        if ".bak" in nl or "mmproj" in nl or "quarantine" in nl:
            continue
        if not gguf.is_file():
            continue
        out.append(gguf)
    # Prefer shallower paths first so top-level wins on basename collisions
    out.sort(key=lambda p: (len(p.parts), str(p).lower()))
    # de-dupe by basename (top-level / shorter path wins)
    seen_names: set = set()
    seen_paths: set = set()
    uniq: List[Path] = []
    for p in out:
        try:
            key = str(p.resolve())
        except Exception:
            key = str(p)
        name_key = p.name.lower()
        if key in seen_paths or name_key in seen_names:
            continue
        seen_paths.add(key)
        seen_names.add(name_key)
        uniq.append(p)
    return uniq


def _seed_candidates_from_local() -> List[Dict[str, Any]]:
    """Invent candidates from C:\\models\\checkpoints_lora (+ registry hints)."""
    cands: List[Dict[str, Any]] = []
    seen = set()

    # Primary authority: live weights on disk
    for models_dir in _MODELS_SEARCH_DIRS:
        if not models_dir.is_dir():
            continue
        for gguf in _iter_ggufs(models_dir):
            key = gguf.name.lower()
            if key in seen:
                continue
            seen.add(key)
            path_s = str(gguf)
            cands.append({
                "name": gguf.name,
                "path": path_s,
                "family": "local",
                "role": "gguf_chat",
                "is_live_default": "qwen2.5-coder-7b-instruct-q5_k_m.gguf" == key,
                "realai_model_id_suggestion": _FILENAME_TO_ID.get(key),
                "vulkan_cmd": (
                    f'C:\\llama-vulkan\\llama-server.exe -m "{path_s}" '
                    f"--host 0.0.0.0 --port 8080 -c 8192 -ngl 40 --jinja"
                ),
            })

    # Keep registry-only entries that still resolve on disk
    reg = _load_registry_file()
    for m in reg.get("models") or []:
        if not isinstance(m, dict):
            continue
        fn = str(m.get("gguf_filename") or Path(str(m.get("gguf_path") or "")).name or "")
        fl = fn.lower()
        if not fn or fl in seen:
            continue
        if ".bak" in fl or "mmproj" in fl or "quarantine" in fl:
            continue
        path = _normalize_path(m.get("gguf_path") or str(_MODELS_DIR / fn))
        if not Path(path).is_file():
            continue
        seen.add(fl)
        cands.append({
            "name": fn,
            "path": path,
            "family": m.get("family") or "local",
            "role": m.get("role") or "gguf_chat",
            "is_live_default": m.get("id") in (
                reg.get("default_model"),
                "realai-default-coder",
                "realai-hive",
            ),
            "realai_model_id_suggestion": m.get("id"),
        })
    return cands


def build_catalog(include_incomplete: bool = False) -> Dict[str, Any]:
    """Build OpenAI-compatible models list with RealAI IDs."""
    # Prefer live GGUFs under C:\models\checkpoints_lora over stale scan maps.
    candidates = _seed_candidates_from_local()
    if not candidates:
        candidates = _load_connect_candidates()
    loaded = vulkan_loaded_model_ids()
    loaded_set = loaded

    models: List[Dict[str, Any]] = []
    used_ids: set = set()
    used_files: set = set()

    for c in candidates:
        if c.get("incomplete_copy") and not include_incomplete:
            continue
        path = _normalize_path(str(c.get("path") or ""))
        name = str(c.get("name") or "")
        file_key = name.lower()
        if file_key in used_files:
            continue
        if ".bak" in file_key or "mmproj" in file_key or "quarantine" in file_key:
            continue
        mid = _suggest_id(c)
        # uniquify only when a different file collides on the same id
        base = mid
        n = 2
        while mid in used_ids:
            mid = f"{base}-{n}"
            n += 1
        used_ids.add(mid)
        used_files.add(file_key)
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
        backend_gguf = os.environ.get(
            "REALAI_BACKEND_MODEL",
            "qwen2.5-coder-7b-instruct-q5_k_m.gguf",
        )
        found = _resolve_existing_gguf(backend_gguf)
        models.append({
            "id": "realai-default-coder",
            "object": "model",
            "created": int(datetime.now(timezone.utc).timestamp()),
            "owned_by": "realai",
            "realai": {
                "display_name": "realai-default-coder",
                "gguf_filename": backend_gguf,
                "gguf_path": str(found or (_MODELS_DIR / backend_gguf)),
                "backend": "llama.cpp-vulkan",
                "backend_model_id": backend_gguf,
                "loaded_now": True,
                "capabilities": ["chat", "completion", "coding"],
            },
        })
        used_ids.add("realai-default-coder")

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

    # Flagship branded chat id: RealAI Hive
    # Points at the primary Vulkan GGUF (7B coder by default; env override supported).
    if "realai-hive" not in used_ids:
        hive_gguf = os.environ.get(
            "REALAI_HIVE_GGUF",
            "qwen2.5-coder-7b-instruct-q5_k_m.gguf",
        )
        hive_path = _resolve_existing_gguf(hive_gguf) or (_MODELS_DIR / Path(hive_gguf).name)
        hive_name = Path(str(hive_path)).name
        hive_live = hive_name.lower() in {str(x).lower() for x in loaded_set} or any(
            hive_name.lower() in str(x).lower() for x in loaded_set
        )
        models.insert(
            0,
            {
                "id": "realai-hive",
                "object": "model",
                "created": int(datetime.now(timezone.utc).timestamp()),
                "owned_by": "realai",
                "permission": [],
                "root": "realai-hive",
                "parent": None,
                "realai": {
                    "display_name": "RealAI Hive",
                    "family": "hive",
                    "role": "gguf_chat",
                    "gguf_path": str(hive_path),
                    "gguf_filename": hive_name,
                    "backend": "llama.cpp-vulkan",
                    "backend_model_id": hive_name,
                    "loaded_now": hive_live,
                    "capabilities": ["chat", "completion", "coding", "hive", "organs"],
                    "source": "branded flagship — organs/hive + Vulkan GGUF",
                    "switch_cmd": (
                        f'C:\\llama-vulkan\\llama-server.exe -m "{hive_path}" '
                        f"--host 0.0.0.0 --port 8080 -c 16384 -ngl 99 --jinja"
                    ),
                },
            },
        )
        used_ids.add("realai-hive")

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

    # Local voice / TTS weight roots under checkpoints_lora
    _VOICE_ROOTS = (
        ("realai-voice-kokoro", Path(r"C:\models\checkpoints_lora\Kokoro"), "kokoro", "kokoro-v1_0.pth"),
        ("realai-voice-fish", Path(r"C:\models\checkpoints_lora\fish_speech_s1"), "fish", "text2semantic-sft-large-v1.1-4k.pth"),
        ("realai-voice-xtts", Path(r"C:\models\checkpoints_lora\xtts_v2"), "xtts", "model.pth"),
    )
    for mid, root, backend, marker in _VOICE_ROOTS:
        if mid in used_ids:
            continue
        present = root.is_dir() and ((root / marker).is_file() or any(root.glob("*")))
        if not present:
            continue
        used_ids.add(mid)
        models.append({
            "id": mid,
            "object": "model",
            "created": int(datetime.now(timezone.utc).timestamp()),
            "owned_by": "realai",
            "permission": [],
            "root": mid,
            "parent": None,
            "realai": {
                "display_name": mid,
                "family": "tts",
                "role": "tts_weights",
                "backend": backend,
                "model_dir": str(root),
                "marker": marker,
                "loaded_now": False,
                "capabilities": ["tts", "speech", "audio"],
                "source": "C:\\models\\checkpoints_lora",
            },
        })

    # Aliases for convenience (legacy + short names → public RealAI ids)
    aliases = {
        "realai-default": "realai-default-coder",
        "realai-default-coder": "realai-default-coder",
        "realai": "realai-hive",
        "default": "realai-hive",
        "hive": "realai-hive",
        "realai hive": "realai-hive",
        "realai-hive": "realai-hive",
        "RealAI Hive": "realai-hive",
        "qwen-coder-7b": "realai-hive",
        "qwen2.5-coder-7b-instruct-q5_k_m.gguf": "realai-hive",
        "qwen2.5-coder-1.5b-instruct-q5_k_m.gguf": "realai-coder-1.5b",
        "realai-coder-1.5b": "realai-coder-1.5b",
        "realai-1.0": "realai-1.0-instruct",
        "llama-local": "local-llama-1b",
        "llama-3.2-1b": "local-llama-1b",
    }
    # only keep aliases that point to existing
    id_set = {m["id"] for m in models}
    aliases = {k: v for k, v in aliases.items() if v in id_set}

    # Prefer env default, then realai-hive, then realai-default-coder
    default_id = None
    env_default = (os.environ.get("REALAI_DEFAULT_MODEL") or "").strip()
    if env_default:
        env_default = aliases.get(env_default, env_default)
        env_default = aliases.get(env_default.lower(), env_default)
        if env_default in id_set:
            default_id = env_default
    if not default_id and "realai-hive" in id_set:
        default_id = "realai-hive"
    if not default_id and "realai-default-coder" in id_set:
        default_id = "realai-default-coder"
    if not default_id:
        for m in models:
            if (m.get("realai") or {}).get("loaded_now") and (m.get("realai") or {}).get("role") != "embeddings":
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

    req = (requested or "").strip() or default_id or "realai-hive"
    # Normalize "RealAI Hive" / spaces / underscores
    req_norm = re.sub(r"[\s_]+", "-", req.strip())
    req = aliases.get(req, aliases.get(req.lower(), aliases.get(req_norm.lower(), req_norm)))

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
