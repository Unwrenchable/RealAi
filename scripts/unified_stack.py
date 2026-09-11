#!/usr/bin/env python3
"""Unified RealAI stack launcher — Vulkan :8080 + orch :8001 + Voice Lab :8890.

Designed for Windows Job Object safety: children are started via
WMI / Start-Process so they survive the launcher exit.

Voice: launches Voice Lab on :8890 and sets REALAI_BOT_VOICE=1 so orch
attaches spoken_text; Hive also synthesizes Kokoro in-process as fallback.

Usage:
  python scripts/unified_stack.py
  python scripts/unified_stack.py --stop
  python scripts/unified_stack.py --no-console
  python scripts/unified_stack.py --no-voice
  python -m realai stack up   # wired to this
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional

def _detect_root() -> Path:
    """Prefer the monorepo root that owns console.html + scripts/."""
    here = Path(__file__).resolve().parents[1]  # .../RealAI-clean
    env = (os.environ.get("REALAI_HOME") or os.environ.get("REALAI_ROOT") or "").strip()
    candidates = []
    if env:
        candidates.append(Path(env))
    candidates.extend([here, here.parent, Path(r"C:\RealAI-clean")])
    for c in candidates:
        try:
            c = c.resolve()
        except Exception:
            continue
        if (c / "console.html").is_file() and (c / "scripts").is_dir():
            return c
        # mistakenly pointed at package dir
        if c.name.lower() == "realai" and (c.parent / "console.html").is_file():
            return c.parent
    return here


ROOT = _detect_root()
VULKAN_DIR = Path(os.environ.get("REALAI_VULKAN_DIR") or r"C:\llama-vulkan")
MODELS_DIR = Path(os.environ.get("REALAI_MODELS_DIR") or r"C:\models\checkpoints_lora")
SERVER_EXE = VULKAN_DIR / "llama-server.exe"
ORCH_PORT = int(os.environ.get("ORCH_PORT") or os.environ.get("REALAI_ORCH_PORT") or "8001")
VULKAN_PORT = int(os.environ.get("REALAI_GPU_PORT") or "8080")
VOICE_LAB_PORT = int(os.environ.get("REALAI_VOICE_LAB_PORT") or "8890")
UI_PORT = int(os.environ.get("REALAI_UI_PORT") or "5173")
LOGS = ROOT / "logs"


def _gguf() -> Path:
    env = (os.environ.get("REALAI_GGUF") or "").strip()
    if env and Path(env).is_file():
        return Path(env)
    # VRAM-safe default 1.5B
    m15 = MODELS_DIR / "qwen2.5-coder-1.5b-instruct-q5_k_m.gguf"
    m7 = MODELS_DIR / "qwen2.5-coder-7b-instruct-q5_k_m.gguf"
    if os.environ.get("REALAI_VRAM_SAFE", "1").lower() not in ("0", "false", "no") and m15.is_file():
        return m15
    if m7.is_file():
        return m7
    if m15.is_file():
        return m15
    raise FileNotFoundError(f"No GGUF under {MODELS_DIR}")


def _url_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= int(getattr(resp, "status", 200) or 200) < 500
    except Exception:
        return False


def _wait_url(url: str, tries: int = 60, sleep_s: float = 2.0) -> bool:
    for i in range(tries):
        if _url_ok(url):
            return True
        time.sleep(sleep_s)
    return False


def _kill_port(port: int) -> List[int]:
    killed: List[int] = []
    if os.name != "nt":
        return killed
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"],
            text=True,
            errors="replace",
        )
    except Exception:
        return killed
    for line in out.splitlines():
        if f":{port}" not in line or "LISTENING" not in line:
            continue
        parts = line.split()
        try:
            pid = int(parts[-1])
        except Exception:
            continue
        if pid <= 0:
            continue
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            killed.append(pid)
        except Exception:
            pass
    return killed


def _base_env() -> Dict[str, str]:
    env = os.environ.copy()
    gguf = str(_gguf())
    env.update(
        {
            "REALAI_HOME": str(ROOT),
            "REALAI_ROOT": str(ROOT),
            "REALAI_WORKSPACE": str(ROOT),
            "REALAI_PRODUCT_ROOT": str(ROOT),
            # Product-root roster file (not nested realai/agents twin; must be agents.json).
            "REALAI_AGENTS_PATH": env.get("REALAI_AGENTS_PATH")
            or str(ROOT / "agents" / "agentx" / "agents.json"),
            "PYTHONPATH": str(ROOT) + os.pathsep + str(ROOT / "realai") + os.pathsep + env.get("PYTHONPATH", ""),
            "PYTHONUNBUFFERED": "1",
            "REALAI_VULKAN_DIR": str(VULKAN_DIR),
            "REALAI_MODELS_DIR": str(MODELS_DIR),
            "REALAI_GGUF": gguf,
            "REALAI_HIVE_GGUF": env.get("REALAI_HIVE_GGUF") or gguf,
            "REALAI_VULKAN_BASE": f"http://127.0.0.1:{VULKAN_PORT}",
            "REALAI_API_BASE": f"http://127.0.0.1:{ORCH_PORT}",
            "ORCH_PORT": str(ORCH_PORT),
            "REALAI_BOT_LOCAL_ONLY": env.get("REALAI_BOT_LOCAL_ONLY") or "1",
            "REALAI_BOT_VOICE": env.get("REALAI_BOT_VOICE") or "1",
            "REALAI_BOT_TOOLS": env.get("REALAI_BOT_TOOLS") or "1",
            "REALAI_SELF_IMPROVE": env.get("REALAI_SELF_IMPROVE") or "1",
            "REALAI_VRAM_SAFE": env.get("REALAI_VRAM_SAFE") or "1",
            "REALAI_DEFAULT_MODEL": env.get("REALAI_DEFAULT_MODEL") or "realai-default-coder",
            # Default: XTTS + unwrenchable clone (Kokoro/Fish/SAPI remain fallbacks).
            "REALAI_TTS_BACKEND": env.get("REALAI_TTS_BACKEND") or "xtts",
            "REALAI_KOKORO_MODEL_DIR": env.get("REALAI_KOKORO_MODEL_DIR")
            or str(MODELS_DIR / "Kokoro"),
            "REALAI_FISH_MODEL_DIR": env.get("REALAI_FISH_MODEL_DIR")
            or str(MODELS_DIR / "fish_speech_s1"),
            "REALAI_XTTS_MODEL_DIR": env.get("REALAI_XTTS_MODEL_DIR")
            or str(MODELS_DIR / "xtts_v2"),
            "REALAI_XTTS_SPEAKER": env.get("REALAI_XTTS_SPEAKER")
            or (
                str(MODELS_DIR / "voices" / "unwrenchable.wav")
                if (MODELS_DIR / "voices" / "unwrenchable.wav").is_file()
                else str(MODELS_DIR / "datasets" / "unwrenchable_voice.wav")
                if (MODELS_DIR / "datasets" / "unwrenchable_voice.wav").is_file()
                else str(MODELS_DIR / "xtts_v2" / "samples" / "en_sample.wav")
            ),
            "REALAI_KOKORO_VOICE": env.get("REALAI_KOKORO_VOICE") or "af_heart",
            "REALAI_VOICE_LAB_PORT": str(VOICE_LAB_PORT),
            "REALAI_VOICE_LAB_URL": env.get("REALAI_VOICE_LAB_URL")
            or f"http://127.0.0.1:{VOICE_LAB_PORT}",
            "REALAI_NGL": env.get("REALAI_NGL") or "40",
            "REALAI_CTX": env.get("REALAI_CTX") or "4096",
        }
    )
    return env


def _start_detached_ps(
    file_path: str,
    arg_list: List[str],
    cwd: str,
    env: Dict[str, str],
    stdout_log: Path,
    stderr_log: Path,
    title: str,
) -> None:
    """Start a child that survives Windows Job Objects.

    Agent/IDE shells often use Job Objects that kill Start-Process children.
    WMI ``Win32_Process.Create`` starts outside that job so orch/vulkan stay up.
    """
    LOGS.mkdir(parents=True, exist_ok=True)
    keys = [
        "PYTHONPATH",
        "REALAI_HOME",
        "REALAI_ROOT",
        "REALAI_WORKSPACE",
        "REALAI_PRODUCT_ROOT",
        "REALAI_AGENTS_PATH",
        "REALAI_VULKAN_BASE",
        "REALAI_API_BASE",
        "REALAI_SELF_IMPROVE",
        "REALAI_BOT_VOICE",
        "REALAI_BOT_TOOLS",
        "REALAI_BOT_LOCAL_ONLY",
        "REALAI_MODELS_DIR",
        "REALAI_GGUF",
        "REALAI_TTS_BACKEND",
        "REALAI_KOKORO_MODEL_DIR",
        "REALAI_FISH_MODEL_DIR",
        "REALAI_XTTS_MODEL_DIR",
        "REALAI_XTTS_SPEAKER",
        "REALAI_KOKORO_VOICE",
        "REALAI_VOICE_LAB_PORT",
        "REALAI_VOICE_LAB_URL",
        "REALAI_VOICE_UI_PORT",
        "ORCH_PORT",
        "PYTHONUNBUFFERED",
    ]
    safe_title = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in (title or "RealAI"))
    bat_path = LOGS / ("_launch_{0}.bat".format(safe_title))
    lines = [
        "@echo off",
        "cd /d \"{0}\"".format(cwd.replace('"', "")),
    ]
    # Prepend venv Scripts only — full PATH often exceeds cmd's ~8191 char line limit
    # and truncates the launch bat (broken quotes → process never stays up).
    py_dir = str(Path(file_path).resolve().parent)
    if py_dir.lower().endswith("scripts"):
        lines.append('set "PATH={0};%PATH%"'.format(py_dir.replace('"', "")))
    for k in keys:
        v = env.get(k)
        if not v:
            continue
        lines.append("set \"{0}={1}\"".format(k, str(v).replace('"', "")))
    quoted_args = []
    for a in arg_list:
        s = str(a)
        if (not s) or any(c in s for c in " \t&|()<>^"):
            quoted_args.append('"{0}"'.format(s.replace('"', "")))
        else:
            quoted_args.append(s)
    cmd_line = '"{0}" {1}'.format(file_path.replace('"', ""), " ".join(quoted_args)).rstrip()
    lines.append(
        "{0} >>\"{1}\" 2>>\"{2}\"".format(
            cmd_line,
            str(stdout_log).replace('"', ""),
            str(stderr_log).replace('"', ""),
        )
    )
    bat_path.write_text("\r\n".join(lines) + "\r\n", encoding="ascii", errors="replace")

    # Prefer WMI create (job-breakaway). Fall back to cmd start.
    wmi_cmd = 'cmd.exe /c ""{0}""'.format(str(bat_path).replace('"', ""))
    ps_wmi = (
        "$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create "
        "-Arguments @{{ CommandLine = '{cmd}'; CurrentDirectory = '{cwd}' }}; "
        "if ($r.ReturnValue -ne 0) {{ exit 1 }}"
    ).format(
        cmd=wmi_cmd.replace("'", "''"),
        cwd=str(cwd).replace("'", "''"),
    )
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            ps_wmi,
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        subprocess.run(
            ["cmd.exe", "/c", "start", title or "RealAI", "/MIN", str(bat_path)],
            check=False,
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def start_vulkan(env: Dict[str, str], force: bool = False) -> Dict[str, Any]:
    health = f"http://127.0.0.1:{VULKAN_PORT}/health"
    if _url_ok(health) and not force:
        return {"ok": True, "status": "already_up", "url": health}
    if not SERVER_EXE.is_file():
        return {"ok": False, "error": f"missing_server:{SERVER_EXE}"}
    gguf = Path(env["REALAI_GGUF"])
    if force:
        _kill_port(VULKAN_PORT)
        time.sleep(1)
    ngl = env.get("REALAI_NGL") or "40"
    ctx = env.get("REALAI_CTX") or "4096"
    _start_detached_ps(
        str(SERVER_EXE),
        [
            "-m",
            str(gguf),
            "--host",
            "127.0.0.1",
            "--port",
            str(VULKAN_PORT),
            "-c",
            str(ctx),
            "-ngl",
            str(ngl),
            "--jinja",
        ],
        str(VULKAN_DIR),
        env,
        LOGS / "vulkan.out.log",
        LOGS / "vulkan.err.log",
        "RealAI-Vulkan",
    )
    ok = _wait_url(health, tries=90, sleep_s=2.0)
    return {
        "ok": ok,
        "status": "started" if ok else "timeout",
        "model": str(gguf),
        "url": health,
        "log": str(LOGS / "vulkan.err.log"),
    }


def start_orch(env: Dict[str, str], force: bool = False) -> Dict[str, Any]:
    health = f"http://127.0.0.1:{ORCH_PORT}/health"
    if _url_ok(health) and not force:
        return {"ok": True, "status": "already_up", "url": f"http://127.0.0.1:{ORCH_PORT}"}
    if force:
        _kill_port(ORCH_PORT)
        time.sleep(1)
    py = sys.executable
    _start_detached_ps(
        py,
        [
            "-m",
            "realai.v3_orchestrator",
            "--host",
            "127.0.0.1",
            "--port",
            str(ORCH_PORT),
        ],
        str(ROOT),
        env,
        LOGS / "v3-orchestrator.out.log",
        LOGS / "v3-orchestrator.err.log",
        "RealAI-Orch",
    )
    ok = _wait_url(health, tries=45, sleep_s=1.0)
    return {
        "ok": ok,
        "status": "started" if ok else "timeout",
        "url": f"http://127.0.0.1:{ORCH_PORT}",
        "voice": env.get("REALAI_BOT_VOICE"),
        "tools": env.get("REALAI_BOT_TOOLS"),
        "log": str(LOGS / "v3-orchestrator.err.log"),
    }


def _voice_lab_python() -> str:
    """Prefer isolated .venv-xtts when present (coqui-tts + pinned transformers)."""
    venv_py = ROOT / ".venv-xtts" / "Scripts" / "python.exe"
    if venv_py.is_file():
        return str(venv_py)
    env_py = (os.environ.get("REALAI_XTTS_PYTHON") or "").strip()
    if env_py and Path(env_py).is_file():
        return env_py
    return sys.executable


def start_voice_lab(env: Dict[str, str], force: bool = False) -> Dict[str, Any]:
    """Launch RealAI Voice Lab on :8890 (detached). Idempotent when healthy."""
    health = f"http://127.0.0.1:{VOICE_LAB_PORT}/health"
    if _url_ok(health) and not force:
        return {
            "ok": True,
            "status": "already_up",
            "url": f"http://127.0.0.1:{VOICE_LAB_PORT}",
        }
    if force:
        _kill_port(VOICE_LAB_PORT)
        time.sleep(1)
    py = _voice_lab_python()
    env = dict(env)
    env.setdefault("REALAI_TTS_BACKEND", "xtts")
    _start_detached_ps(
        py,
        [
            "-m",
            "realai.voice.lab_server",
            "--host",
            "127.0.0.1",
            "--port",
            str(VOICE_LAB_PORT),
        ],
        str(ROOT),
        env,
        LOGS / "voice-lab.out.log",
        LOGS / "voice-lab.err.log",
        "RealAI-VoiceLab",
    )
    # First XTTS/Kokoro import can be slow — give it time.
    ok = _wait_url(health, tries=60, sleep_s=1.0)
    return {
        "ok": ok,
        "status": "started" if ok else "timeout",
        "url": f"http://127.0.0.1:{VOICE_LAB_PORT}",
        "python": py,
        "log": str(LOGS / "voice-lab.err.log"),
        "note": "GET /health · POST /v1/audio/speech · XTTS default (Kokoro fallback)",
    }


def start_voice_studio(env: Dict[str, str], force: bool = False) -> Dict[str, Any]:
    """Launch full Voice Lab Studio UI (Speak/Clone/Train) on :8787, job-breakaway."""
    ui_port = int(os.environ.get("REALAI_VOICE_UI_PORT") or "8787")
    url = f"http://127.0.0.1:{ui_port}/"
    if _url_ok(url) and not force:
        return {"ok": True, "status": "already_up", "url": url}
    voice_pkg = ROOT / "realai" / "voice"
    pkg_json = voice_pkg / "package.json"
    if not pkg_json.is_file():
        return {"ok": False, "status": "missing_package", "url": url, "error": str(pkg_json)}
    npm = Path(r"C:\Program Files\nodejs\npm.cmd")
    if not npm.is_file():
        # fall through PATH lookup later via cmd
        npm_s = "npm.cmd"
    else:
        npm_s = str(npm)
    if force:
        _kill_port(ui_port)
        time.sleep(1)
    env = dict(env)
    env["REALAI_VOICE_LAB_URL"] = env.get("REALAI_VOICE_LAB_URL") or f"http://127.0.0.1:{VOICE_LAB_PORT}"
    # Detached via WMI so the vite process survives the launcher Job Object.
    _start_detached_ps(
        npm_s,
        ["run", "dev"],
        str(voice_pkg),
        env,
        LOGS / "voice-lab-ui.out.log",
        LOGS / "voice-lab-ui.err.log",
        "RealAI-VoiceStudio",
    )
    ok = _wait_url(url, tries=90, sleep_s=1.0)
    return {
        "ok": ok,
        "status": "started" if ok else "timeout",
        "url": url,
        "log": str(LOGS / "voice-lab-ui.err.log"),
        "note": "Speak · Clone · Pipeline/train — full Studio",
    }


def stack_status() -> Dict[str, Any]:
    vulkan = _url_ok(f"http://127.0.0.1:{VULKAN_PORT}/health")
    orch = _url_ok(f"http://127.0.0.1:{ORCH_PORT}/health")
    voice_lab = _url_ok(f"http://127.0.0.1:{VOICE_LAB_PORT}/health")
    kokoro = _url_ok("http://127.0.0.1:8880/health") or _url_ok("http://127.0.0.1:8880/v1/models")
    ui = _url_ok(f"http://127.0.0.1:{UI_PORT}/") or _url_ok(f"http://127.0.0.1:{UI_PORT}")
    console_url = f"http://127.0.0.1:{ORCH_PORT}/console"
    return {
        "ok": vulkan and orch,
        "vulkan": {"ok": vulkan, "url": f"http://127.0.0.1:{VULKAN_PORT}"},
        "orchestrator": {"ok": orch, "url": f"http://127.0.0.1:{ORCH_PORT}"},
        "voice_lab": {
            "ok": voice_lab,
            "url": f"http://127.0.0.1:{VOICE_LAB_PORT}",
            "note": "RealAI Voice Lab — launched with stack; Hub probes this for Voice OK",
        },
        "hive_ui_optional": {
            "ok": ui,
            "url": f"http://127.0.0.1:{UI_PORT}",
            "note": "TanStack console — npm run dev / start_ui.bat (local RealAI only, no xAI)",
        },
        "kokoro_optional": {
            "ok": kokoro,
            "url": "http://127.0.0.1:8880",
            "note": "optional dedicated Kokoro HTTP; Lab/Hive use in-process Kokoro when this is down",
        },
        "console": console_url,
        "console_file": str(ROOT / "console.html"),
        "voice_mode": "Voice Lab :8890 + Hive /v1/audio/speech (Kokoro) + browser speechSynthesis fallback",
        "provider": "realai-local",
    }


def stack_up(
    *,
    force: bool = False,
    open_console: bool = True,
    voice_lab: bool = True,
) -> Dict[str, Any]:
    env = _base_env()
    # Apply env to current process too
    os.environ.update(env)
    LOGS.mkdir(parents=True, exist_ok=True)
    vul = start_vulkan(env, force=force)
    orch = start_orch(env, force=force)
    voice = (
        start_voice_lab(env, force=force)
        if voice_lab
        else {"ok": False, "status": "skipped", "url": f"http://127.0.0.1:{VOICE_LAB_PORT}"}
    )
    studio = (
        start_voice_studio(env, force=force)
        if voice_lab
        else {"ok": False, "status": "skipped", "url": "http://127.0.0.1:8787/"}
    )
    status = stack_status()
    console_url = f"http://127.0.0.1:{ORCH_PORT}/console"
    if open_console and status.get("ok"):
        try:
            webbrowser.open(console_url)
        except Exception as e:
            status["console_error"] = str(e)
    return {
        "ok": bool(vul.get("ok") and orch.get("ok")),
        "vulkan": vul,
        "orchestrator": orch,
        "voice_lab": voice,
        "voice_studio": studio,
        "status": status,
        "env": {
            "REALAI_BOT_VOICE": env.get("REALAI_BOT_VOICE"),
            "REALAI_BOT_TOOLS": env.get("REALAI_BOT_TOOLS"),
            "REALAI_GGUF": env.get("REALAI_GGUF"),
            "REALAI_TTS_BACKEND": env.get("REALAI_TTS_BACKEND"),
            "REALAI_VOICE_LAB_URL": env.get("REALAI_VOICE_LAB_URL"),
        },
    }


def stack_down() -> Dict[str, Any]:
    killed_v = _kill_port(VULKAN_PORT)
    killed_o = _kill_port(ORCH_PORT)
    killed_voice = _kill_port(VOICE_LAB_PORT)
    # also llama-server by name
    try:
        subprocess.run(
            ["taskkill", "/IM", "llama-server.exe", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        pass
    return {
        "ok": True,
        "killed_ports": {
            VULKAN_PORT: killed_v,
            ORCH_PORT: killed_o,
            VOICE_LAB_PORT: killed_voice,
        },
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Unified RealAI stack launcher")
    ap.add_argument("--stop", action="store_true", help="Stop vulkan + orch + voice lab")
    ap.add_argument("--status", action="store_true", help="Print health only")
    ap.add_argument("--force", action="store_true", help="Restart even if up")
    ap.add_argument("--no-console", action="store_true", help="Do not open console.html")
    ap.add_argument("--no-voice", action="store_true", help="Do not launch Voice Lab :8890")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args(argv)

    if args.stop:
        payload = stack_down()
    elif args.status:
        payload = stack_status()
    else:
        payload = stack_up(
            force=args.force,
            open_console=not args.no_console,
            voice_lab=not args.no_voice,
        )

    if args.json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        if args.stop:
            print("stack down:", payload)
        elif args.status:
            print(
                "vulkan={0} orch={1} voice_lab={2}".format(
                    payload["vulkan"]["ok"],
                    payload["orchestrator"]["ok"],
                    (payload.get("voice_lab") or {}).get("ok"),
                )
            )
            print("console:", payload.get("console"))
            print("voice_lab:", (payload.get("voice_lab") or {}).get("url"))
            print("voice:", payload.get("voice_mode"))
        else:
            print("vulkan:", payload["vulkan"].get("status"), payload["vulkan"].get("model"))
            print("orch:   ", payload["orchestrator"].get("status"), payload["orchestrator"].get("url"))
            vl = payload.get("voice_lab") or {}
            print("voice:  ", vl.get("status"), vl.get("url"), "·", vl.get("note") or "")
            print("console:", payload.get("status", {}).get("console"))
            if payload.get("ok"):
                print("OK — stack up (Vulkan + Hive + Voice Lab). Hard-refresh console if already open.")
            else:
                print("INCOMPLETE — check logs under", LOGS)
                return 1
    return 0 if payload.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
