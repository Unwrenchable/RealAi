#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ENTRIES = [
    {
        "id": "hierarchical_specialists",
        "name": "hierarchical_specialists",
        "source": "abilities/hierarchical_specialists.py",
        "type": "ability",
        "status": "CODE",
        "capabilities": [
            "researcher",
            "coder",
            "creative",
            "executor",
            "critic",
            "specialist_tools",
        ],
        "modules": [
            "abilities/hierarchical_specialists.py",
            "core/agents/agents.py",
            "core/agents/tools.py",
        ],
        "secrets_policy": "none",
        "note": "Promoted gold specialists into core/agents",
    },
    {
        "id": "approval_store",
        "name": "approval_store",
        "source": "abilities/approval_store.py",
        "type": "ability",
        "status": "CODE",
        "capabilities": ["approval", "human_gate"],
        "modules": [
            "abilities/approval_store.py",
            "realai/plugins/tools/approval_store.py",
        ],
        "secrets_policy": "none",
    },
    {
        "id": "device_selector",
        "name": "device_selector",
        "source": "abilities/device_selector.py",
        "type": "ability",
        "status": "CODE",
        "capabilities": ["device", "directml", "cuda", "cpu"],
        "modules": [
            "abilities/device_selector.py",
            "realai/plugins/tools/device_selector.py",
        ],
        "secrets_policy": "none",
    },
]


def upsert_catalog(aid: str, name: str, modules: list[str], live: str) -> None:
    cat = ROOT / "realai" / "ability_catalog.py"
    text = cat.read_text(encoding="utf-8")
    if f'"id": "{aid}"' in text:
        return
    block = (
        "    {\n"
        f'        "id": "{aid}",\n'
        f'        "name": "{name}",\n'
        '        "pillar": "advanced",\n'
        f'        "keywords": ["{aid.replace("_", " ")}", "{aid}"],\n'
        '        "status": "CODE",\n'
        f'        "live_path": "{live}",\n'
        f'        "modules": {json.dumps(modules)},\n'
        "    },\n"
    )
    for marker in (
        '    {\n        "id": "plugin_system"',
        '    {\n        "id": "memory_learning"',
        '    {\n        "id": "deep_promote"',
    ):
        if marker in text:
            cat.write_text(text.replace(marker, block + marker, 1), encoding="utf-8")
            return


def main() -> int:
    reg_path = ROOT / "realai" / "abilities" / "registry.json"
    data = json.loads(reg_path.read_text(encoding="utf-8"))
    ids = {a.get("id"): i for i, a in enumerate(data.get("abilities") or [])}
    for e in ENTRIES:
        if e["id"] in ids:
            data["abilities"][ids[e["id"]]] = e
        else:
            data.setdefault("abilities", []).append(e)
        upsert_catalog(e["id"], e["name"], e["modules"], e["source"])
    reg_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("registry", len(data["abilities"]))

    from abilities.approval_store import run as approval_run
    from abilities.device_selector import run as device_run
    from abilities.hierarchical_specialists import run as hs_run

    print("hs", hs_run(context={"action": "list"}).get("ok"))
    print("approval", approval_run(context={"action": "list"}).get("ok"))
    print("device", device_run())

    from realai.ability_catalog import save_catalog

    print(save_catalog())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
