"""Device profile + model recommendation for RealAI (local-first, never the iGPU by accident).

collect()   -> hardware report: OS, CPU, RAM, GPUs (Vulkan list from llama-server --list-devices,
               DirectML adapters, Win32_VideoController / registry VRAM, lspci / sysfs), robot hints
               (serial ports, GPIO, ROS env).
recommend() -> model + quant + ctx + llama-server --device + DirectML adapter, computed from the
               report with the size table below (pure function; tests and the dataset use it).

CLI: python -m realai.core.device_profile [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Qwen2.5 Instruct family: (params label, layers, kv_heads, head_dim, Q5_K_M GB, Q4_K_M GB).
# File sizes are the published GGUF sizes (approx.), KV cache = 2 * layers * kv_heads * head_dim * 2 bytes/token (f16).
MODELS = [
    ("32B", 64, 8, 128, 23.3, 19.9),
    ("14B", 48, 8, 128, 10.5, 8.99),
    ("7B", 28, 4, 128, 5.44, 4.68),
    ("3B", 36, 2, 128, 2.22, 1.93),
    ("1.5B", 28, 2, 128, 1.13, 0.99),
    ("0.5B", 24, 2, 64, 0.42, 0.40),
]
CTX_LADDER = [32768, 16384, 8192, 4096, 2048]
OVERHEAD_GB = 0.8          # compute buffers + driver
GPU_BUDGET = 0.90          # usable fraction of dedicated VRAM
CPU_BUDGET = 0.50          # usable fraction of system RAM when no discrete GPU
IGPU_PAT = re.compile(r"(\(tm\) graphics$|radeon graphics$|radeon\(tm\) graphics|vega \d+ graphics|"
                      r"intel\(r\) (uhd|hd|iris)|intel(?!.*\barc\b).*graphics|microsoft basic|llvmpipe|swiftshader)", re.I)


def kv_gb_per_token(layers: int, kv_heads: int, head_dim: int) -> float:
    return 2 * layers * kv_heads * head_dim * 2 / 2 ** 30


def is_integrated(name: str, vram_gb: Optional[float] = None) -> bool:
    n = (name or "").strip()
    if IGPU_PAT.search(n):
        return True
    return vram_gb is not None and vram_gb < 1.5


# ----------------------------------------------------------------------------- collection
def _run(cmd: List[str], timeout: int = 20) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout or ""
    except Exception:
        return ""


def parse_llama_list_devices(text: str) -> List[Dict[str, Any]]:
    """`llama-server --list-devices` lines like 'Vulkan0: AMD Radeon RX 6700 XT (12272 MiB, 11000 MiB free)'."""
    out = []
    for m in re.finditer(r"^\s*([A-Za-z]+\d+):\s*(.+?)\s*\((\d+)\s*MiB(?:,\s*(\d+)\s*MiB free)?\)", text, re.M):
        out.append({"id": m.group(1), "name": m.group(2).strip(), "vram_gb": round(int(m.group(3)) / 1024, 2),
                    "free_gb": round(int(m.group(4)) / 1024, 2) if m.group(4) else None})
    return out


def _llama_server() -> Optional[str]:
    for c in (os.environ.get("REALAI_LLAMA_SERVER"), r"C:\llama-vulkan\llama-server.exe", shutil.which("llama-server")):
        if c and Path(c).is_file():
            return c
    return None


def _windows_gpus() -> List[Dict[str, Any]]:
    gpus: List[Dict[str, Any]] = []
    try:  # registry has the real 64-bit VRAM (Win32_VideoController.AdapterRAM caps at 4 GB)
        import winreg

        key = r"SYSTEM\ControlSet001\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as k:
            for i in range(64):
                try:
                    sub = winreg.EnumKey(k, i)
                except OSError:
                    break
                if not sub.isdigit():
                    continue
                try:
                    with winreg.OpenKey(k, sub) as s:
                        name = winreg.QueryValueEx(s, "DriverDesc")[0]
                        try:
                            mem = int(winreg.QueryValueEx(s, "HardwareInformation.qwMemorySize")[0])
                        except OSError:
                            mem = None
                        gpus.append({"name": name, "vram_gb": round(mem / 2 ** 30, 2) if mem else None, "source": "registry"})
                except OSError:
                    continue
    except Exception:
        pass
    if gpus:  # registry keeps one key per driver install: dedupe by name, keep the largest VRAM
        best: Dict[str, Dict[str, Any]] = {}
        for g in gpus:
            k = g["name"].lower()
            if k not in best or (g.get("vram_gb") or 0) > (best[k].get("vram_gb") or 0):
                best[k] = g
        gpus = list(best.values())
    if not gpus:
        txt = _run(["powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_VideoController | Select Name,AdapterRAM | ConvertTo-Json"])
        try:
            data = json.loads(txt or "[]")
            for g in data if isinstance(data, list) else [data]:
                gpus.append({"name": g.get("Name"), "vram_gb": round((g.get("AdapterRAM") or 0) / 2 ** 30, 2) or None,
                             "source": "Win32_VideoController"})
        except Exception:
            pass
    return gpus


def _linux_gpus() -> List[Dict[str, Any]]:
    gpus = []
    for line in _run(["lspci", "-mm"]).splitlines():
        if re.search(r'"(VGA|3D|Display)', line):
            parts = re.findall(r'"([^"]*)"', line)
            gpus.append({"name": " ".join(parts[1:3]).strip(), "vram_gb": None, "source": "lspci"})
    for card in sorted(Path("/sys/class/drm").glob("card[0-9]")):
        f = card / "device" / "mem_info_vram_total"
        if f.is_file() and gpus:
            try:
                gpus[min(int(card.name[4:]), len(gpus) - 1)]["vram_gb"] = round(int(f.read_text()) / 2 ** 30, 2)
            except Exception:
                pass
    return gpus


def _directml() -> List[str]:
    try:
        import torch_directml as d

        return [d.device_name(i).replace("\x00", "").strip() for i in range(d.device_count())]
    except Exception:
        return []


def _ram_gb() -> Optional[float]:
    try:
        import psutil

        return round(psutil.virtual_memory().total / 2 ** 30, 1)
    except Exception:
        pass
    if Path("/proc/meminfo").is_file():
        m = re.search(r"MemTotal:\s+(\d+)", Path("/proc/meminfo").read_text())
        return round(int(m.group(1)) / 2 ** 20, 1) if m else None
    if os.name == "nt":
        try:
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                            ("avail", ctypes.c_ulonglong), ("a", ctypes.c_ulonglong), ("b", ctypes.c_ulonglong),
                            ("c", ctypes.c_ulonglong), ("d", ctypes.c_ulonglong), ("e", ctypes.c_ulonglong)]

            ms = MS(); ms.l = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
            return round(ms.total / 2 ** 30, 1)
        except Exception:
            return None
    return None


def _hints() -> Dict[str, Any]:
    serial: List[str] = []
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DEVICEMAP\SERIALCOMM") as k:
                i = 0
                while True:
                    try:
                        serial.append(winreg.EnumValue(k, i)[1]); i += 1
                    except OSError:
                        break
        except Exception:
            pass
    else:
        for pat in ("ttyUSB*", "ttyACM*", "ttyAMA*", "serial*"):
            serial += [str(p) for p in Path("/dev").glob(pat)]
    gpio = bool(list(Path("/dev").glob("gpiochip*"))) or Path("/sys/class/gpio").exists() if os.name != "nt" else False
    return {"serial_ports": sorted(serial), "gpio": gpio,
            "ros": {k: os.environ[k] for k in ("ROS_DISTRO", "ROS_VERSION", "ROS_DOMAIN_ID") if k in os.environ}}


def collect() -> Dict[str, Any]:
    gpus = _windows_gpus() if os.name == "nt" else _linux_gpus()
    srv = _llama_server()
    vulkan = parse_llama_list_devices(_run([srv, "--list-devices"])) if srv else []
    return {
        "os": f"{platform.system()} {platform.release()}", "machine": platform.machine(),
        "cpu": platform.processor() or platform.machine(), "cpu_threads": os.cpu_count(),
        "ram_gb": _ram_gb(), "gpus": gpus, "vulkan_devices": vulkan, "directml_adapters": _directml(),
        "llama_server": srv, "hints": _hints(),
    }


# ----------------------------------------------------------------------------- recommendation
def _discrete(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Discrete GPUs, merged across sources; VRAM preference: Vulkan > registry/sysfs."""
    seen: Dict[str, Dict[str, Any]] = {}
    for g in profile.get("gpus") or []:
        if g.get("name") and not is_integrated(g["name"], g.get("vram_gb")):
            seen[g["name"].lower()] = {"name": g["name"], "vram_gb": g.get("vram_gb")}
    for v in profile.get("vulkan_devices") or []:
        if is_integrated(v["name"], v.get("vram_gb")):
            continue
        cur = seen.setdefault(v["name"].lower(), {"name": v["name"]})
        cur["vram_gb"] = v.get("vram_gb") or cur.get("vram_gb")
        cur["vulkan_id"] = v["id"]
    return sorted((g for g in seen.values() if g.get("vram_gb")), key=lambda g: -g["vram_gb"])


def fit(budget_gb: float) -> Optional[Dict[str, Any]]:
    """Largest model/quant whose weights + KV(ctx) + overhead fit; prefers ctx >= 8192, then 4096, then 2048."""
    for min_ctx in (8192, 4096, 2048):  # agent work wants >= 8k context first
        for label, layers, kvh, hd, q5, q4 in MODELS:
            for quant, w in (("Q5_K_M", q5), ("Q4_K_M", q4)):
                for ctx in CTX_LADDER:
                    if ctx < min_ctx:
                        break
                    need = w + kv_gb_per_token(layers, kvh, hd) * ctx + OVERHEAD_GB
                    if need <= budget_gb:
                        return {"model": f"Qwen2.5-{label}-Instruct", "quant": quant, "ctx": ctx,
                                "need_gb": round(need, 2), "weights_gb": w}
    return None


def recommend(profile: Dict[str, Any]) -> Dict[str, Any]:
    gpus = _discrete(profile)
    integrated = sorted({g["name"] for g in (profile.get("gpus") or []) + (profile.get("vulkan_devices") or [])
                         if is_integrated(g.get("name", ""), g.get("vram_gb"))})
    rec: Dict[str, Any] = {"integrated_ignored": integrated, "reasons": []}
    if gpus:
        g = gpus[0]
        budget = round(g["vram_gb"] * GPU_BUDGET, 2)
        pick = fit(budget)
        rec.update(target="gpu", gpu=g["name"], vram_gb=g["vram_gb"], budget_gb=budget, **(pick or {}))
        dml = [i for i, n in enumerate(profile.get("directml_adapters") or []) if n.lower() == g["name"].lower()]
        rec["llama_server_args"] = (["--device", g["vulkan_id"]] if g.get("vulkan_id") else []) + \
            ["-ngl", "99", "-c", str(rec.get("ctx", 4096))]
        rec["dml_adapter"] = g["name"] if dml else None
        rec["dml_index"] = dml[0] if dml else None
        rec["reasons"].append(f"discrete GPU {g['name']} with {g['vram_gb']} GB; budget {budget} GB (90%)")
        if integrated:
            rec["reasons"].append("ignoring integrated GPU(s): " + ", ".join(integrated))
    else:
        ram = profile.get("ram_gb") or 0
        budget = round(ram * CPU_BUDGET, 2)
        pick = fit(min(budget, 8.0))  # CPU decode: keep to <= 8 GB of weights+KV for usable speed
        rec.update(target="cpu", budget_gb=budget, **(pick or {}))
        rec["llama_server_args"] = ["-ngl", "0", "-c", str(rec.get("ctx", 2048)), "-t", str(max(1, (profile.get("cpu_threads") or 2) // 2))]
        rec["dml_adapter"] = None
        rec["reasons"].append(f"no discrete GPU; CPU with {ram} GB RAM, budget {budget} GB (50%, capped at 8 GB)")
    if "model" not in rec:
        rec["reasons"].append("nothing fits; use a smaller quant or more memory")
    h = profile.get("hints") or {}
    if h.get("serial_ports") or h.get("gpio") or h.get("ros"):
        rec["robot_hints"] = {k: h[k] for k in ("serial_ports", "gpio", "ros") if h.get(k)}
        rec["reasons"].append("robot/sensor hints present: keep a model loaded locally; no cloud dependency")
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m realai.core.device_profile")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    prof = collect()
    out = {"profile": prof, "recommendation": recommend(prof)}
    if a.json:
        print(json.dumps(out, indent=2))
    else:
        r = out["recommendation"]
        print(f"{prof['os']} | RAM {prof['ram_gb']} GB | GPUs: {', '.join(g['name'] for g in prof['gpus']) or 'none'}")
        print(f"-> {r.get('model')} {r.get('quant')} ctx {r.get('ctx')} on {r.get('gpu') or 'CPU'}; llama-server {' '.join(r['llama_server_args'])}")
        for x in r["reasons"]:
            print("   -", x)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
