import json
import re
from pathlib import Path
import sys

# Permanent UTF‑8 fix
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

ABILITY_REGISTRY = Path("abilities/registry.json")

SEARCH_ROOTS = [
    Path("abilities"),
    Path("modules"),
    Path("agent_tools"),
    Path("agents"),
    Path("realai"),
]

def extract_ability_from_python(path: Path):
    """
    Detect ability definitions inside Python files.
    Looks for patterns like:
        class AbilityName(Ability):
        def ability_name(self, ...)
        ABILITY = {...}
    """
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    # JSON-style ability manifest inside Python
    json_patterns = [
        r"ABILITY\s*=\s*({.*?})",
        r"ABILITY_MANIFEST\s*=\s*({.*?})",
    ]

    for pat in json_patterns:
        matches = re.findall(pat, text, flags=re.DOTALL)
        for m in matches:
            try:
                return json.loads(m)
            except Exception:
                continue

    # Class-based ability definition
    class_match = re.search(r"class\s+(\w+)\s*\(\s*Ability\s*\)", text)
    if class_match:
        name = class_match.group(1)
        return {
            "name": name,
            "source": str(path),
            "type": "class",
            "capabilities": []
        }

    # Function-based ability definition
    func_matches = re.findall(r"def\s+(ability_\w+)\s*\(", text)
    if func_matches:
        return {
            "name": func_matches[0],
            "source": str(path),
            "type": "function",
            "capabilities": []
        }

    return None

def extract_tool_from_python(path: Path):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    matches = re.findall(r"TOOL\s*=\s*({.*?})", text, flags=re.DOTALL)
    for m in matches:
        try:
            return json.loads(m)
        except Exception:
            continue

    return None

def extract_task_from_python(path: Path):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    matches = re.findall(r"TASK\s*=\s*({.*?})", text, flags=re.DOTALL)
    for m in matches:
        try:
            return json.loads(m)
        except Exception:
            continue

    return None

def scan_all_components():
    abilities = []
    tools = []
    tasks = []

    for root in SEARCH_ROOTS:
        if not root.exists():
            continue

        print(f"[auto-wire] scanning {root} ...")

        for p in root.rglob("*.py"):
            ability = extract_ability_from_python(p)
            if ability:
                abilities.append(ability)
                print(f"  + ability {ability['name']}")

            tool = extract_tool_from_python(p)
            if tool:
                tools.append(tool)
                print(f"  + tool {tool.get('name', p.stem)}")

            task = extract_task_from_python(p)
            if task:
                tasks.append(task)
                print(f"  + task {task.get('name', p.stem)}")

    return abilities, tools, tasks

def main():
    abilities, tools, tasks = scan_all_components()

    registry = {
        "abilities": abilities,
        "tools": tools,
        "tasks": tasks,
    }

    ABILITY_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    ABILITY_REGISTRY.write_text(json.dumps(registry, indent=2), encoding="utf-8")

    print(f"[auto-wire] wrote {ABILITY_REGISTRY}")
    print(f"[auto-wire] abilities={len(abilities)} tools={len(tools)} tasks={len(tasks)}")

if __name__ == "__main__":
    main()
