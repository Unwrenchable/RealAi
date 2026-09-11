from pathlib import Path
from core.orchestrator import Orchestrator

def launch_runtime():
    root = Path(r"C:\models\checkpoints_lora")
    orch = Orchestrator(root)
    orch.run()
