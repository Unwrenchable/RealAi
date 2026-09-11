"""Merge missing agents / packs / profiles from agent_tools_ into RealAI."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

EXT = Path(r"C:\Users\tsmit\agent_tools_")
ROOT = Path(r"C:\RealAI-clean")
LIVE = ROOT / "realai" / "agents" / "agentx" / "agents.json"
PROD = ROOT / "agents" / "agentx" / "agents.json"


def load_agents(path: Path) -> list:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else list(data.get("agents") or [])


def merge(path: Path, ext_by_id: dict) -> tuple[list[str], int]:
    cur = load_agents(path)
    have = {a.get("id") for a in cur}
    added: list[str] = []
    for aid, agent in sorted(ext_by_id.items()):
        if aid not in have:
            cur.append(agent)
            added.append(aid)
    cur.sort(key=lambda a: (a.get("id") or ""))
    path.write_text(json.dumps(cur, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return added, len(cur)


def main() -> None:
    ext_agents = json.loads(
        (EXT / "agent_tools" / "data" / "agents.json").read_text(encoding="utf-8")
    )
    ext_by_id = {a["id"]: a for a in ext_agents}

    a1, n1 = merge(LIVE, ext_by_id)
    a2, n2 = merge(PROD, ext_by_id)
    print(f"live added {len(a1)} -> {n1}")
    for x in a1:
        print(" ", x)
    print(f"prod added {len(a2)} -> {n2}")

    prof_src = EXT / "agent_tools" / "data" / "access_profiles.json"
    for dest in [
        ROOT / "realai" / "agents" / "agentx" / "access_profiles.json",
        ROOT / "agents" / "agentx" / "access_profiles.json",
    ]:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(prof_src, dest)
        print("profiles ->", dest)

    pack_dests = [ROOT / "agents", ROOT / "realai" / "agents"]
    copied: list[str] = []
    for src in (EXT / "agents").iterdir():
        if not src.is_file():
            continue
        if src.suffix == ".agentx" or src.name.endswith(".agent.json"):
            for d in pack_dests:
                d.mkdir(parents=True, exist_ok=True)
                target = d / src.name
                if not target.exists():
                    shutil.copy2(src, target)
                    copied.append(str(target))
    print("packs copied", len(copied))
    for c in copied:
        print(" ", c)

    wf_dest = ROOT / "agents" / "workflows"
    wf_dest.mkdir(parents=True, exist_ok=True)
    for src in (EXT / "examples").glob("workflow-*.json"):
        t = wf_dest / src.name
        if not t.exists():
            shutil.copy2(src, t)
            print("workflow", t)


if __name__ == "__main__":
    main()
