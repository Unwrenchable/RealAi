from pathlib import Path
from core.auto_model_detector import AutoModelDetector

def main():
    model_root = Path(r"C:\models\checkpoints_lora")
    out = Path(r"C:\RealAI-clean\model_catalog.json")

    detector = AutoModelDetector(model_root, out)
    registry = detector.run()

    print("[AutoModelDetector] Model catalog written to:", out)
    print(json.dumps(registry, indent=2))

if __name__ == "__main__":
    main()
