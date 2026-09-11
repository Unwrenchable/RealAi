"""
RealAI GPU backend inspector — Vulkan llama-server + checkpoints_lora.

Honest about VRAM: train pauses server; resume restores chat.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def _scripts_dir(workspace: Path) -> Path:
    return workspace / "scripts"


def _load_runtime(workspace: Path):
    scripts = _scripts_dir(workspace)
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import vulkan_runtime  # type: ignore

    return vulkan_runtime


def inspect(workspace: Path) -> Dict[str, Any]:
    try:
        vr = _load_runtime(workspace)
    except Exception as e:
        return {
            "ok": False,
            "error": f"vulkan_runtime unavailable: {e}",
            "expected": {
                "exe": r"C:\llama-vulkan\llama-server.exe",
                "cli": r"C:\llama-vulkan\llama-cli.exe",
                "models": r"C:\models\checkpoints_lora",
            },
        }
    paths = vr.paths()
    health = vr.health()
    port_up = vr.port_up()
    return {
        "ok": bool(health.get("ok")),
        "port_up": port_up,
        "health": health,
        "paths": paths,
        "env": {
            "REALAI_GGUF": os.environ.get("REALAI_GGUF"),
            "REALAI_NGL": os.environ.get("REALAI_NGL"),
            "REALAI_CTX": os.environ.get("REALAI_CTX"),
            "REALAI_VRAM_SAFE": os.environ.get("REALAI_VRAM_SAFE", "1"),
        },
        "note": "LoRA/Craft train may pause llama-server for VRAM; use resume after.",
    }


def resume(workspace: Path, gguf: Optional[str] = None, *, force: bool = False) -> Dict[str, Any]:
    vr = _load_runtime(workspace)
    return vr.resume_vulkan(gguf or None, force_restart=force, wait_s=120.0)


def stop(workspace: Path) -> Dict[str, Any]:
    vr = _load_runtime(workspace)
    return {"ok": True, "stopped": vr.pause_vulkan()}
