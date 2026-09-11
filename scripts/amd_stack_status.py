#!/usr/bin/env python3
"""
AMD stack status: Vulkan chat (llama-vulkan) + orchestrator + DirectML train.

  python scripts/amd_stack_status.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
PRESETS = ROOT / "config" / "train_presets.json"


def ping(url: str, timeout: float = 2.0) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            body = r.read()[:500]
            return {"ok": True, "status": r.status, "body": body.decode("utf-8", "replace")[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main() -> int:
    os.environ.setdefault("REALAI_DIRECTML_DIR", r"C:\DirectML\runtime\x64")
    dml_dir = os.environ.get("REALAI_DIRECTML_DIR", "")
    if dml_dir and Path(dml_dir).is_dir():
        os.environ["PATH"] = dml_dir + os.pathsep + os.environ.get("PATH", "")

    vulkan = ping("http://127.0.0.1:8080/health")
    orch = ping("http://127.0.0.1:8001/health")

    llama = Path(r"C:\llama-vulkan\llama-server.exe")
    dml_dll = Path(r"C:\DirectML\runtime\x64\DirectML.dll")

    backends = {"directml": False, "cuda": False, "cpu": True}
    try:
        import torch

        backends["torch"] = torch.__version__
        backends["cuda"] = bool(torch.cuda.is_available())
    except Exception as e:
        backends["torch_error"] = str(e)
    try:
        import torch_directml

        backends["directml"] = int(torch_directml.device_count()) > 0
        backends["directml_device"] = str(torch_directml.device())
        backends["directml_count"] = int(torch_directml.device_count())
    except Exception as e:
        backends["directml_error"] = f"{type(e).__name__}: {e}"

    presets = {}
    if PRESETS.is_file():
        presets = json.loads(PRESETS.read_text(encoding="utf-8")).get("presets") or {}

    out = {
        "chat_inference": {
            "llama_server_exe": str(llama),
            "llama_server_exists": llama.is_file(),
            "vulkan_health": vulkan,
            "orchestrator_health": orch,
            "start": "powershell -ExecutionPolicy Bypass -File C:\\RealAI-clean\\scripts\\run_local_chat.ps1",
        },
        "train": {
            "directml_dll": str(dml_dll),
            "directml_dll_exists": dml_dll.is_file(),
            "backends": backends,
            "dataset": r"C:\models\checkpoints_lora\normalized_datasets\realai_lora_ready.jsonl",
            "presets": list(presets.keys()),
            "train_cmd_example": "python scripts/train_lora_local.py --preset qwen-coder-1.5b --device directml --max-steps 50",
        },
        "split": {
            "vulkan": "GGUF chat via C:\\llama-vulkan (GPU inference)",
            "orchestrator": "tools/proxy on :8001 -> Vulkan :8080",
            "directml": "LoRA training on RX 6700 XT (does not replace Vulkan chat)",
        },
    }

    print(json.dumps(out, indent=2))
    print()
    print("Vulkan chat :", "UP" if vulkan.get("ok") else "DOWN", " http://127.0.0.1:8080/health")
    print("Orchestrator:", "UP" if orch.get("ok") else "DOWN", " http://127.0.0.1:8001/health")
    print(
        "DirectML    :",
        "OK" if backends.get("directml") else "NO",
        backends.get("directml_device") or backends.get("directml_error") or "",
    )
    print("Presets     :", ", ".join(presets.keys()) or "(none)")
    return 0 if vulkan.get("ok") and orch.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
