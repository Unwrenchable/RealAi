"""Import C:\\tmp\\agency-agents markdown personas into RealAI registries.

- Parses via agent_tools.importer
- Skips strategy/docs/examples noise
- Additive merge (does not clobber richer existing agents)
- Saves agency_import.json + copies markdown under agents/agency/
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from agent_tools.importer import import_agency_agents, parse_markdown_agent

ROOT = Path(r"C:\RealAI-clean")
SOURCE = Path(r"C:\tmp\agency-agents")
LIVE = ROOT / "realai" / "agents" / "agentx" / "agents.json"
PROD = ROOT / "agents" / "agentx" / "agents.json"
AGENCY_IMPORT = ROOT / "agents" / "agentx" / "agency_import.json"
AGENCY_MD = ROOT / "agents" / "agency"
WORKFLOWS = ROOT / "agents" / "workflows"

AGENT_DIRS = {
    "academic",
    "design",
    "engineering",
    "finance",
    "game-development",
    "marketing",
    "paid-media",
    "product",
    "project-management",
    "sales",
    "spatial-computing",
    "specialized",
    "support",
    "testing",
}

SKIP_IDS = {
    "agent-activation-prompts",
    "executive-brief",
    "handoff-templates",
    "nexus-strategy",
    "quickstart",
    "readme",
}


def _is_noise(agent_id: str) -> bool:
    if agent_id in SKIP_IDS:
        return True
    if agent_id.startswith("phase-") or agent_id.startswith("scenario-"):
        return True
    if "workflow-" in agent_id:
        return True
    return False


def _load(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else list(data.get("agents") or [])


def _clean_tags(tags: list) -> list[str]:
    out: list[str] = []
    for t in tags or []:
        s = str(t).strip()
        if not s or len(s) > 48:
            continue
        if " " in s and len(s.split()) > 4:
            continue
        out.append(s)
    # de-dupe preserve order
    seen: set[str] = set()
    clean: list[str] = []
    for t in out:
        if t.lower() in seen:
            continue
        seen.add(t.lower())
        clean.append(t)
    return clean[:8]


def _from_category_tree() -> list[dict]:
    """Parse only agent category folders (skip strategy/examples/integrations)."""
    imported: dict[str, dict] = {}
    for category in sorted(AGENT_DIRS):
        base = SOURCE / category
        if not base.is_dir():
            continue
        for path in base.rglob("*.md"):
            if path.name.lower() == "readme.md":
                continue
            parsed = parse_markdown_agent(path)
            if not parsed:
                continue
            aid = str(parsed["id"])
            if _is_noise(aid):
                continue
            parsed["tags"] = _clean_tags(list(parsed.get("tags") or []) + [category])
            parsed["source"] = "agency-agents"
            parsed["source_path"] = str(path.relative_to(SOURCE)).replace("\\", "/")
            imported[aid] = parsed
    return sorted(imported.values(), key=lambda a: str(a["id"]))


def _merge(path: Path, incoming: list[dict]) -> tuple[int, int, int]:
    cur = _load(path)
    by_id = {str(a.get("id")): a for a in cur if isinstance(a, dict) and a.get("id")}
    added = enriched = 0
    for item in incoming:
        aid = str(item["id"])
        prev = by_id.get(aid)
        if prev is None:
            by_id[aid] = item
            added += 1
            continue
        # Enrich empty/short fields only — never clobber richer RealAI entries
        changed = False
        for key in ("description", "role"):
            new_v = str(item.get(key) or "")
            old_v = str(prev.get(key) or "")
            if new_v and len(new_v) > len(old_v) + 20:
                prev[key] = new_v
                changed = True
        for key in ("tags", "capabilities", "required_tools"):
            new_l = list(item.get(key) or [])
            old_l = list(prev.get(key) or [])
            if key == "tags":
                new_l = _clean_tags(new_l)
            merged = list(dict.fromkeys([*old_l, *new_l]))
            if key == "tags":
                merged = _clean_tags(merged)
            if merged != old_l and (not old_l or len(merged) > len(old_l)):
                prev[key] = merged[:12] if key != "required_tools" else merged
                changed = True
        for key in ("preferred_profile", "risk_level"):
            if not prev.get(key) and item.get(key):
                prev[key] = item[key]
                changed = True
        if item.get("source_path") and not prev.get("source_path"):
            prev["source"] = item.get("source") or "agency-agents"
            prev["source_path"] = item["source_path"]
            changed = True
        if changed:
            enriched += 1
        by_id[aid] = prev
    merged = sorted(by_id.values(), key=lambda a: str(a.get("id") or ""))
    path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return added, enriched, len(merged)


def _copy_markdown(incoming: list[dict]) -> int:
    AGENCY_MD.mkdir(parents=True, exist_ok=True)
    n = 0
    for item in incoming:
        rel = item.get("source_path")
        if not rel:
            continue
        src = SOURCE / str(rel)
        if not src.is_file():
            continue
        dest = AGENCY_MD / str(rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists() or dest.stat().st_mtime < src.stat().st_mtime:
            shutil.copy2(src, dest)
            n += 1
    return n


def _copy_workflows() -> list[str]:
    WORKFLOWS.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    examples = SOURCE / "examples"
    if not examples.is_dir():
        return copied
    for src in examples.glob("workflow-*.md"):
        dest = WORKFLOWS / src.name
        if not dest.exists():
            shutil.copy2(src, dest)
            copied.append(str(dest))
    return copied


def main() -> None:
    # Prefer category-scoped parse; fall back to full importer filter
    incoming = _from_category_tree()
    if not incoming:
        incoming = [
            a
            for a in import_agency_agents(str(SOURCE))
            if not _is_noise(str(a["id"]))
        ]
        for a in incoming:
            a["tags"] = _clean_tags(list(a.get("tags") or []))
            a["source"] = "agency-agents"

    AGENCY_IMPORT.write_text(
        json.dumps(incoming, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    a1, e1, n1 = _merge(LIVE, incoming)
    a2, e2, n2 = _merge(PROD, incoming)
    md_n = _copy_markdown(incoming)
    wfs = _copy_workflows()

    print(f"agency_agents_parsed={len(incoming)}")
    print(f"live added={a1} enriched={e1} total={n1}")
    print(f"prod added={a2} enriched={e2} total={n2}")
    print(f"markdown_copied={md_n} -> {AGENCY_MD}")
    print(f"agency_import -> {AGENCY_IMPORT}")
    print(f"workflows_copied={len(wfs)}")
    for w in wfs:
        print(" ", w)

    # Highlight high-value new ids for RealAI
    live_ids = {a["id"] for a in _load(LIVE)}
    highlight = [
        "ai-engineer",
        "code-reviewer",
        "security-engineer",
        "sre",
        "threat-detection-engineer",
        "voice-ai-integration-engineer",
        "software-architect",
        "minimal-change-engineer",
        "codebase-onboarding-engineer",
        "incident-response-commander",
        "game-audio-engineer",
        "level-designer",
        "narrative-designer",
        "unity-architect",
        "reality-checker",
        "evidence-collector",
        "mcp-builder",
        "model-qa-specialist",
        "workflow-architect",
        "chief-of-staff",
    ]
    print("highlight_present:")
    for hid in highlight:
        print(f"  {'YES' if hid in live_ids else 'NO '} {hid}")


if __name__ == "__main__":
    main()
