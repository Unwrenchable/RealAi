#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ENTRY = {
    "id": "deep_promote",
    "name": "Deep promote (named roots + nests)",
    "pillar": "advanced",
    "keywords": [
        "deep promote",
        "nested gold",
        "thin wrap",
        "promote deep",
        "function diff",
    ],
    "status": "LIVE",
    "live_path": "abilities/deep_promote.py + craft /promote",
    "modules": [
        "abilities/deep_promote.py",
        "scripts/deep_promote_scan.py",
        "scripts/deep_promote_wire.py",
        "realai/cli/craft.py",
    ],
}


def main() -> int:
    reg_path = ROOT / "realai" / "abilities" / "registry.json"
    data = json.loads(reg_path.read_text(encoding="utf-8"))
    ids = {a.get("id"): i for i, a in enumerate(data.get("abilities") or [])}
    reg_entry = {
        "id": "deep_promote",
        "name": "deep_promote",
        "source": "abilities/deep_promote.py",
        "type": "ability",
        "status": "LIVE",
        "capabilities": ["deep_promote", "nested_gold", "thin_wrap", "dispatch"],
        "modules": ENTRY["modules"],
        "secrets_policy": "none",
        "note": "Runs real scan+wire scripts and verifies artifacts",
    }
    if "deep_promote" in ids:
        data["abilities"][ids["deep_promote"]] = reg_entry
    else:
        data.setdefault("abilities", []).append(reg_entry)
    reg_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("registry ok")

    cat = ROOT / "realai" / "ability_catalog.py"
    text = cat.read_text(encoding="utf-8")
    if '"id": "deep_promote"' not in text:
        block = (
            "    {\n"
            '        "id": "deep_promote",\n'
            '        "name": "Deep promote (named roots + nests)",\n'
            '        "pillar": "advanced",\n'
            '        "keywords": ["deep promote", "nested gold", "thin wrap", "promote deep", "function diff"],\n'
            '        "status": "LIVE",\n'
            '        "live_path": "abilities/deep_promote.py + craft /promote",\n'
            '        "modules": [\n'
            '            "abilities/deep_promote.py",\n'
            '            "scripts/deep_promote_scan.py",\n'
            '            "scripts/deep_promote_wire.py",\n'
            '            "realai/cli/craft.py",\n'
            "        ],\n"
            "    },\n"
        )
        for marker in (
            '    {\n        "id": "plugin_system"',
            '    {\n        "id": "memory_learning"',
            '    {\n        "id": "coach"',
        ):
            if marker in text:
                cat.write_text(text.replace(marker, block + marker, 1), encoding="utf-8")
                print("catalog py ok")
                break
        else:
            print("catalog py marker missing")
    else:
        print("catalog py already has deep_promote")

    from realai.ability_catalog import save_catalog

    print(save_catalog())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
