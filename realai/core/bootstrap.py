from pathlib import Path
from core.runtime import launch_runtime

def bootstrap():
    print("[Bootstrap] Initializing RealAI...")
    launch_runtime()

if __name__ == "__main__":
    bootstrap()
