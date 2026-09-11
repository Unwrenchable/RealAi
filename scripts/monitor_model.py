import json
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

MODEL = Path("model.json")
LOG = Path("performance.log")

REQUIRED_FIELDS = [
    "version",
    "accuracy",
    "latency",
    "world_model",
    "plugins",
    "agent_runtime"
]

def safe_read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def repair_model(model: dict) -> bool:
    repaired = False
    for field in REQUIRED_FIELDS:
        if field not in model:
            model[field] = "missing"
            repaired = True
    return repaired

def main():
    lines = ["=== RealAI Self-Improve Monitor (one-shot) ==="]

    if not MODEL.exists():
        lines.append("model.json missing — creating skeleton")
        model = {f: "missing" for f in REQUIRED_FIELDS}
        MODEL.write_text(json.dumps(model, indent=2), encoding="utf-8")
        lines.append("Created model.json with required fields")
    else:
        model = safe_read_json(MODEL)
        repaired = repair_model(model)
        if repaired:
            MODEL.write_text(json.dumps(model, indent=2), encoding="utf-8")
            lines.append("Repaired missing fields in model.json")
        else:
            lines.append("model.json already has all required fields")

    lines.append(f"Model snapshot: {json.dumps(model, indent=2)}")
    LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"[monitor] wrote {LOG}")

if __name__ == "__main__":
    main()