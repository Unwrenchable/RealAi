import subprocess
import time
import os
import requests

ROOT = r"C:\RealAI-clean"

MODEL = os.path.join(ROOT, "models", "qwen2.5-coder-7b-instruct-q5_k_m.gguf")
LLAMA_SERVER = r"C:\llama-vulkan\llama-server.exe"

# ✔ Correct orchestrator entrypoint
ORCH = os.path.join(ROOT, "realai", "v3_orchestrator.py")

GPU_URL = "http://127.0.0.1:8080/health"
ORCH_URL = "http://127.0.0.1:8001/health"

def start_gpu_server():
    print("[RealAI Runtime] Starting GPU server...")
    return subprocess.Popen([
        LLAMA_SERVER,
        "--model", MODEL,
        "--port", "8080"
    ])

def wait_for(url, name, timeout=60):
    print(f"[RealAI Runtime] Waiting for {name}...")
    for _ in range(timeout):
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                print(f"[RealAI Runtime] {name} is online.")
                return True
        except:
            pass
        time.sleep(1)
    print(f"[RealAI Runtime] WARNING: {name} did not come online.")
    return False

def start_orchestrator():
    print("[RealAI Runtime] Starting orchestrator...")
    return subprocess.Popen(["python", ORCH])

def start_chat():
    print("[RealAI Runtime] Starting chat runtime...")
    subprocess.Popen(["python", "-m", "realai", "chat"])

def main():
    print("==============================================")
    print(" RealAI Unified Runtime Loader (GPU Enabled)  ")
    print("==============================================")

    # GPU server (non-blocking)
    start_gpu_server()
    wait_for(GPU_URL, "GPU Server")

    # Orchestrator (non-blocking)
    start_orchestrator()
    wait_for(ORCH_URL, "Orchestrator")

    # Chat (non-blocking)
    start_chat()

    print("[RealAI Runtime] All systems launched.")
    print("[RealAI Runtime] GPU + Orchestrator + Chat are active.")

if __name__ == "__main__":
    main()
