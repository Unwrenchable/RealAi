"""Import novel Vault77 + Overseer agents into RealAI registries."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

LIVE = Path(r"C:\RealAI-clean\realai\agents\agentx\agents.json")
PROD = Path(r"C:\RealAI-clean\agents\agentx\agents.json")
SNAP = Path(r"C:\RealAI-clean\agents\agentx\vault77_overseer_import.json")
PERSONA_DIR = Path(r"C:\RealAI-clean\agents\from_vault77_overseer")

SOURCES = [
    (
        "vault77",
        Path(r"C:\Users\tsmit\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS\.agentx\agents.json"),
        ("vault77-",),
    ),
    (
        "overseer_ai",
        Path(r"C:\Users\tsmit\overseer-bot-ai\.agentx\agents.json"),
        ("overseer-", "overseer_"),
    ),
    (
        "overseer_ui",
        Path(r"C:\Users\tsmit\overseer-bot-ui\.agentx\agents.json"),
        ("overseer-", "overseer_"),
    ),
]


def load_list(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [a for a in data if isinstance(a, dict) and a.get("id")]
    if isinstance(data, dict) and isinstance(data.get("agents"), list):
        return [a for a in data["agents"] if isinstance(a, dict) and a.get("id")]
    return []


def wanted(agent: dict, prefixes: tuple[str, ...]) -> bool:
    aid = str(agent.get("id") or "").lower()
    return any(aid.startswith(p) for p in prefixes)


def normalize(agent: dict, source: str) -> dict:
    out = dict(agent)
    tags = list(out.get("tags") or [])
    if source not in tags:
        tags.append(source)
    if "imported" not in tags:
        tags.append("imported")
    out["tags"] = tags
    out.setdefault("source", source)
    # ensure required fields for activity UI
    out.setdefault("role", out.get("id"))
    out.setdefault("description", "")
    out.setdefault("capabilities", [])
    out.setdefault("required_tools", [])
    out.setdefault("preferred_profile", "balanced")
    out.setdefault("risk_level", "medium")
    return out


def merge(path: Path, incoming: list[dict]) -> tuple[int, int]:
    cur = load_list(path) if path.is_file() else []
    by_id = {str(a["id"]): a for a in cur}
    added = enriched = 0
    for item in incoming:
        aid = str(item["id"])
        prev = by_id.get(aid)
        if prev is None:
            by_id[aid] = item
            added += 1
            continue
        changed = False
        for key in ("description", "role"):
            new_v = str(item.get(key) or "")
            old_v = str(prev.get(key) or "")
            if new_v and len(new_v) > len(old_v) + 20:
                prev[key] = new_v
                changed = True
        for key in ("tags", "capabilities", "required_tools"):
            merged = list(dict.fromkeys([*(prev.get(key) or []), *(item.get(key) or [])]))
            if merged != list(prev.get(key) or []):
                prev[key] = merged
                changed = True
        if changed:
            enriched += 1
        by_id[aid] = prev
    out = sorted(by_id.values(), key=lambda a: str(a.get("id") or ""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return added, enriched


def main() -> None:
    incoming: list[dict] = []
    seen: set[str] = set()
    for source, path, prefixes in SOURCES:
        if not path.is_file():
            print("missing", path)
            continue
        for agent in load_list(path):
            if not wanted(agent, prefixes):
                continue
            aid = str(agent["id"])
            if aid in seen:
                continue
            seen.add(aid)
            incoming.append(normalize(agent, source))

    SNAP.write_text(json.dumps(incoming, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    PERSONA_DIR.mkdir(parents=True, exist_ok=True)
    # keep a copy of source packs for provenance
    for source, path, _ in SOURCES:
        if path.is_file():
            shutil.copy2(path, PERSONA_DIR / f"{source}_agents.json")

    a1, e1 = merge(LIVE, incoming)
    a2, e2 = merge(PROD, incoming)
    print(f"selected={len(incoming)}")
    for a in incoming:
        print(" ", a["id"])
    print(f"live added={a1} enriched={e1} total={len(load_list(LIVE))}")
    print(f"prod added={a2} enriched={e2} total={len(load_list(PROD))}")
    print("snapshot", SNAP)
    print("personas", PERSONA_DIR)


if __name__ == "__main__":
    main()
