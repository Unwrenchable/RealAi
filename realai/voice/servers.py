"""Probe local GPU chat + TTS HTTP backends used by the hive bot."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from .paths import (
    DIRECTML_DIR,
    FISH_URL,
    HIVE_URL,
    KOKORO_URL,
    LLAMA_DIR,
    VULKAN_BASE,
    VULKAN_DIR,
    XTTS_URL,
    directml_runtime_dll,
    llama_server_exe,
    llama_tts_exe,
)


def _probe(url: str, timeout: float = 0.6) -> Dict[str, Any]:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(4096)
            body: Any
            try:
                body = json.loads(raw.decode("utf-8", errors="replace"))
            except Exception:
                body = raw[:200].decode("utf-8", errors="replace")
            return {"ok": True, "url": url, "status": getattr(resp, "status", 200), "body": body}
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)[:200]}


def probe_vulkan() -> Dict[str, Any]:
    out = _probe(f"{VULKAN_BASE}/health")
    out["exe"] = str(llama_server_exe()) if llama_server_exe() else None
    out["dir"] = str(VULKAN_DIR if VULKAN_DIR.is_dir() else LLAMA_DIR)
    return out


def probe_hive() -> Dict[str, Any]:
    return _probe(f"{HIVE_URL}/health")


def probe_kokoro() -> Dict[str, Any]:
    hit = _probe(f"{KOKORO_URL}/health")
    hit["backend"] = "kokoro"
    if hit.get("ok"):
        return hit
    return {"ok": False, "backend": "kokoro", "url": KOKORO_URL, "error": hit.get("error") or "unreachable"}


def probe_fish() -> Dict[str, Any]:
    hit = _probe(f"{FISH_URL}/health")
    hit["backend"] = "fish"
    if hit.get("ok"):
        return hit
    return {"ok": False, "backend": "fish", "url": FISH_URL, "error": hit.get("error") or "unreachable"}


def probe_xtts() -> Dict[str, Any]:
    hit = _probe(f"{XTTS_URL}/health")
    hit["backend"] = "xtts"
    if hit.get("ok"):
        return hit
    return {"ok": False, "backend": "xtts", "url": XTTS_URL, "error": hit.get("error") or "unreachable"}


def stack_health(quick: bool = True) -> Dict[str, Any]:
    """Single health snapshot for Voice Lab + hive bot.

    quick=True: only Vulkan + Hive (fast /health). TTS probes are optional.
    """
    dll = directml_runtime_dll()
    out: Dict[str, Any] = {
        "provider": "realai",
        "vulkan": probe_vulkan(),
        "hive": probe_hive(),
        "bins": {
            "llama_server": str(llama_server_exe()) if llama_server_exe() else None,
            "llama_tts": str(llama_tts_exe()) if llama_tts_exe() else None,
            "directml_dll": str(dll) if dll else None,
            "directml_dir_exists": DIRECTML_DIR.is_dir(),
            "vulkan_dir_exists": VULKAN_DIR.is_dir(),
            "llama_dir_exists": LLAMA_DIR.is_dir(),
        },
    }
    if not quick:
        out["tts"] = {
            "kokoro": probe_kokoro(),
            "fish": probe_fish(),
            "xtts": probe_xtts(),
        }
    return out


def preferred_tts_http() -> Optional[str]:
    """Return first reachable neural TTS base URL, else None."""
    for name, probe in (
        ("kokoro", probe_kokoro),
        ("fish", probe_fish),
        ("xtts", probe_xtts),
    ):
        hit = probe()
        if hit.get("ok"):
            return name
    return None
