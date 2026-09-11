"""Universal Doctor — read-only diagnostics across mapped worlds."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from realai.universe.worlds import list_worlds, primary_workspace


def diagnose(workspace: Path | None = None) -> Dict[str, Any]:
    ws = primary_workspace(workspace)
    checks: List[Tuple[str, bool, str]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    add("workspace", ws.is_dir(), str(ws))
    add(
        "universe_env",
        (os.environ.get("REALAI_UNIVERSE") or "").lower() in {"1", "true", "yes", "on"},
        os.environ.get("REALAI_UNIVERSE") or "",
    )
    add("package_universe", (ws / "realai" / "universe" / "mode.py").is_file(), "realai.universe")
    add("hive_agents", (ws / ".github" / "agents").is_dir(), str(ws / ".github" / "agents"))
    add("world_model_json", (ws / "realai" / "world_model.json").is_file(), "do not overwrite gold")
    gguf = os.environ.get("REALAI_GGUF") or r"C:\models\checkpoints_lora\qwen2.5-coder-7b-instruct-q5_k_m.gguf"
    add("default_gguf", Path(gguf).is_file(), gguf)
    vulkan = Path(os.environ.get("REALAI_VULKAN_DIR") or r"C:\llama-vulkan") / "llama-server.exe"
    add("llama-server.exe", vulkan.is_file(), str(vulkan))
    worlds = list_worlds(ws)
    add("worlds_mapped", len(worlds) >= 1, f"count={len(worlds)}")

    failed = [n for n, ok, _ in checks if not ok]
    return {
        "ok": len(failed) == 0,
        "name": "Universal Doctor",
        "workspace": str(ws),
        "worlds": len(worlds),
        "checks": {n: {"ok": ok, "detail": d} for n, ok, d in checks},
        "failed": failed,
        "note": "Read-only. Does not run heal, promote, or start servers.",
    }