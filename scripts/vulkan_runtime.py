#!/usr/bin/env python3
"""
Shared AMD Vulkan llama-server control for RealAI Hive.

Binaries : C:\\llama-vulkan\\llama-server.exe (+ llama-cli.exe)
Weights  : C:\\models\\checkpoints_lora\\*.gguf

Craft / DirectML LoRA train kills llama-server to free VRAM.
Call resume_vulkan() after training so chat (:8080) comes back.
"""
from __future__ import annotations

import os
import socket
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

VULKAN_DIR = Path(os.environ.get("REALAI_VULKAN_DIR") or r"C:\llama-vulkan")
MODELS_DIR = Path(os.environ.get("REALAI_MODELS_DIR") or r"C:\models\checkpoints_lora")
SERVER_EXE = VULKAN_DIR / "llama-server.exe"
CLI_EXE = VULKAN_DIR / "llama-cli.exe"
HOST = os.environ.get("REALAI_GPU_HOST") or "127.0.0.1"
PORT = int(os.environ.get("REALAI_GPU_PORT") or "8080")

# Default: 7B Q5 from checkpoints_lora (GPU chat). Override with REALAI_GGUF.
# Keep 1.5B as fallback only when 7B is missing.
_RESUME_CANDIDATES = [
    os.environ.get("REALAI_TRAIN_RESUME_GGUF") or "",
    os.environ.get("REALAI_GGUF") or "",
    os.environ.get("REALAI_HIVE_GGUF") or "",
    os.environ.get("REALAI_MODEL_PATH") or "",
    str(MODELS_DIR / "qwen2.5-coder-7b-instruct-q5_k_m.gguf"),
    str(MODELS_DIR / "qwen2.5-coder-1.5b-instruct-q5_k_m.gguf"),
    str(MODELS_DIR / "realai-1.0-instruct-Q4_K_M.gguf"),
    str(MODELS_DIR / "Llama-3.2-1B-Instruct-Q4_K_M.gguf"),
]


def log(msg: str) -> None:
    print(f"[vulkan] {msg}", flush=True)


def port_up(port: int = PORT, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((HOST, port), timeout=timeout):
            return True
    except OSError:
        return False


def health(timeout: float = 3.0) -> Dict[str, Any]:
    url = f"http://{HOST}:{PORT}/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")[:300]
            return {"ok": resp.status == 200, "status": resp.status, "body": body, "url": url}
    except Exception as e:
        return {"ok": False, "error": str(e), "url": url}


def resolve_gguf(preferred: Optional[str] = None) -> Path:
    ordered = [preferred or ""] + list(_RESUME_CANDIDATES)
    seen = set()
    for raw in ordered:
        if not raw:
            continue
        p = Path(raw)
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        if p.is_file():
            return p
        # bare filename under MODELS_DIR
        cand = MODELS_DIR / p.name
        if cand.is_file():
            return cand
    # last resort: smallest existing gguf
    if MODELS_DIR.is_dir():
        ggufs = sorted(MODELS_DIR.glob("*.gguf"), key=lambda x: x.stat().st_size, reverse=True)
        if ggufs:
            return ggufs[0]
    raise FileNotFoundError(
        f"No GGUF found under {MODELS_DIR}. Set REALAI_GGUF or REALAI_TRAIN_RESUME_GGUF."
    )


def pause_vulkan() -> List[str]:
    """Kill llama-server to free AMD VRAM for DirectML / Craft LoRA train."""
    stopped: List[str] = []
    for name in ("llama-server.exe", "llama-server"):
        try:
            r = subprocess.run(
                ["taskkill", "/IM", name, "/F"],
                capture_output=True,
                text=True,
            )
            out = (r.stdout or "") + (r.stderr or "")
            if r.returncode == 0 or "SUCCESS" in out.upper():
                stopped.append(name)
        except Exception as e:
            log(f"pause warning ({name}): {e}")
    # brief settle so VRAM is released
    time.sleep(1.0)
    if stopped:
        log(f"paused for VRAM: {stopped}")
    else:
        log("pause: no llama-server process found")
    return stopped


def resume_vulkan(
    gguf: Optional[str] = None,
    *,
    ngl: Optional[int] = None,
    ctx: Optional[int] = None,
    wait_s: float = 90.0,
    force_restart: bool = False,
) -> Dict[str, Any]:
    """
    Start llama-server.exe with a GGUF from checkpoints_lora.

    Defaults favor 7B Q5 from checkpoints_lora with high ctx + full GPU offload. Override via REALAI_GGUF.
    """
    if not SERVER_EXE.is_file():
        return {"ok": False, "error": "missing_server", "path": str(SERVER_EXE)}

    if port_up() and not force_restart:
        h = health()
        if h.get("ok"):
            return {"ok": True, "status": "already_up", "health": h}

    if force_restart or port_up():
        pause_vulkan()

    try:
        model = resolve_gguf(gguf)
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e)}

    ngl_v = int(ngl if ngl is not None else (os.environ.get("REALAI_NGL") or "99"))
    ctx_v = int(ctx if ctx is not None else (os.environ.get("REALAI_CTX") or "65536"))

    args = [
        str(SERVER_EXE),
        "-m",
        str(model),
        "--host",
        HOST,
        "--port",
        str(PORT),
        "-c",
        str(ctx_v),
        "-ngl",
        str(ngl_v),
        "--jinja",
    ]
    log(f"starting {SERVER_EXE.name} model={model.name} ngl={ngl_v} ctx={ctx_v}")

    try:
        if os.name == "nt":
            # WMI Win32_Process.Create starts outside the parent Job Object.
            # Start-Process/Popen children are still reaped when tooling shells exit.
            cmdline = subprocess.list2cmdline(args)
            ps = (
                "$r = ([wmiclass]'Win32_Process').Create({cmd!r}, {cwd!r}); "
                "if ($r.ReturnValue -ne 0) {{ exit $r.ReturnValue }} "
                "Write-Output $r.ProcessId"
            ).format(cmd=cmdline, cwd=str(VULKAN_DIR))
            completed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    ps,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if completed.returncode != 0:
                return {
                    "ok": False,
                    "error": f"wmi_start_failed:rc={completed.returncode}",
                    "stderr": (completed.stderr or "")[-500:],
                    "model": str(model),
                }
        else:
            subprocess.Popen(
                args,
                cwd=str(VULKAN_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
    except Exception as e:
        return {"ok": False, "error": f"start_failed: {e}", "model": str(model)}
    deadline = time.time() + max(10.0, wait_s)
    while time.time() < deadline:
        if port_up():
            h = health(timeout=2.0)
            if h.get("ok"):
                # confirm a model is actually loaded (not empty router)
                try:
                    with urllib.request.urlopen(
                        f"http://{HOST}:{PORT}/v1/models", timeout=3.0
                    ) as resp:
                        raw = resp.read().decode("utf-8", errors="replace")
                    loaded = '"id"' in raw or '"data"' in raw
                except Exception:
                    loaded = False
                return {
                    "ok": True,
                    "status": "started",
                    "model": str(model),
                    "exe": str(SERVER_EXE),
                    "cli": str(CLI_EXE) if CLI_EXE.is_file() else None,
                    "models_dir": str(MODELS_DIR),
                    "health": h,
                    "models_endpoint_ok": loaded,
                    "url": f"http://{HOST}:{PORT}/v1",
                }
        time.sleep(1.5)

    return {
        "ok": False,
        "status": "timeout",
        "model": str(model),
        "hint": f"Check {VULKAN_DIR} and {model}",
    }


def paths() -> Dict[str, Any]:
    return {
        "vulkan_dir": str(VULKAN_DIR),
        "server_exe": str(SERVER_EXE),
        "server_exists": SERVER_EXE.is_file(),
        "cli_exe": str(CLI_EXE),
        "cli_exists": CLI_EXE.is_file(),
        "models_dir": str(MODELS_DIR),
        "models_dir_exists": MODELS_DIR.is_dir(),
        "default_resume_gguf": str(resolve_gguf()) if MODELS_DIR.is_dir() else None,
        "port": PORT,
        "host": HOST,
    }


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Pause/resume RealAI Vulkan llama-server")
    ap.add_argument("action", choices=["status", "pause", "resume", "paths"])
    ap.add_argument("--gguf", default="", help="Override GGUF path/filename")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if args.action == "paths":
        print(json.dumps(paths(), indent=2))
    elif args.action == "status":
        print(json.dumps({"port_up": port_up(), "health": health(), **paths()}, indent=2))
    elif args.action == "pause":
        print(json.dumps({"stopped": pause_vulkan()}, indent=2))
    else:
        print(json.dumps(resume_vulkan(args.gguf or None, force_restart=args.force), indent=2))
