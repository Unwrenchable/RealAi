from pathlib import Path
import json
import glob

OUT_DIR = Path(__file__).resolve().parents[1] / 'datasets' / 'processed'
OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

def normalize_agent_tool_log(entry):
    """Convert a raw agent-tool log entry into a training sample."""
    messages = []

    if "user" in entry:
        messages.append({"role": "user", "content": entry["user"]})

    if "agent" in entry:
        messages.append({"role": "assistant", "content": entry["agent"]})

    if "tool_input" in entry:
        messages.append({"role": "assistant", "content": f"<tool:{entry.get('tool_name','unknown')}>{entry['tool_input']}"})

    if "tool_output" in entry:
        messages.append({"role": "tool", "content": entry["tool_output"]})

    if "final" in entry:
        messages.append({"role": "assistant", "content": entry["final"]})

    return {"messages": messages}

def extract_agent_tool_data(input_root=None, output_root=None):
    input_root = Path(input_root or "realai/logs/agent-tools")
    output_dir = Path(output_root or OUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    out_path = output_dir / "instructions.jsonl"

    with out_path.open("w", encoding="utf-8") as handle:
        for file in glob.glob(str(input_root / "*.json")):
            raw = load_json(file)
            if not raw:
                continue

            sample = normalize_agent_tool_log(raw)
            handle.write(json.dumps(sample) + "\n")

    return {"instructions": str(out_path)}

def main():
    return extract_agent_tool_data()

if __name__ == "__main__":
    main()
