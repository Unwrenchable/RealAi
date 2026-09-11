from pathlib import Path
import json

def tool_architect_mode(
    prompt_path: str = r"C:\RealAI-clean\prompts\architect_mode.txt",
    snapshot_path: str = r"C:\RealAI-clean\results\repo_snapshot.json",
    output_path: str = r"C:\RealAI-clean\results\architect_plan.md",
) -> str:
    """
    High-level architecture / planning mode.
    Reads the architect prompt + current repo snapshot and produces a structured plan.
    """
    prompt_file = Path(prompt_path)
    snapshot_file = Path(snapshot_path)
    out_file = Path(output_path)

    if not prompt_file.exists():
        return f"ERROR: architect prompt not found at {prompt_file}"

    if not snapshot_file.exists():
        return f"ERROR: repo snapshot not found at {snapshot_file}. Run a snapshot first."

    architect_prompt = prompt_file.read_text(encoding="utf-8")
    snapshot = json.loads(snapshot_file.read_text(encoding="utf-8"))

    # Very basic skeleton – replace this with real LLM call later
    plan = f"""# Architect Mode Plan
Generated from: {snapshot_file.name}

## Prompt Summary
{architect_prompt[:800]}...

## Repo Snapshot Overview
- Total files: {len(snapshot.get('files', []))}
- Key directories: {list(snapshot.get('dirs', {}).keys())[:20]}

## Recommended Next Actions
1. ...
2. ...
3. ...

(Replace this stub with a real model call using the architect_prompt + snapshot)
"""

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(plan, encoding="utf-8")

    return f"Architect plan written to {out_file}\n\n{plan[:1500]}..."