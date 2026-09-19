#!/usr/bin/env python3
"""Sync Agency markdown specialists + other repo agent defs into Hive registries.

Writes:
  - agents/agentx/agency_import.json
  - agents/agentx/agents.json  (merge, preserve hive/multi cores)
  - modules/agents_skills/agentx/agency_import.json (mirror)
  - modules/agents_skills/agentx/agents.json (mirror if present)

  python scripts/sync_agency_registry.py
  python scripts/sync_agency_registry.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_tools.realai_ish_importer import (  # noqa: E402
    import_agency_agents,
    parse_markdown_agent,
)

AGENCY_DIR = ROOT / "agents" / "agency"
AGENTX = ROOT / "agents" / "agentx"
MIRROR = ROOT / "modules" / "agents_skills" / "agentx"
LOG = ROOT / "docs" / "recovery" / "2026-09-19-agency-registry-sync.json"

HIVE_IDS = {
    "overseer",
    "coder",
    "architect",
    "analyst",
    "memory",
    "governor",
    "router",
    "hive-orchestrator",
}
MULTI_IDS = {
    "researcher",
    "creative",
    "executor",
    "critic",
    "hive-orchestrator",
    "ai-orchestrator",
}


def _ensure_tags(tags: List[str], *extra: str) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for t in list(tags) + list(extra):
        t = str(t or "").strip().lower()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _load_json_list(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict) and isinstance(data.get("agents"), list):
        return [x for x in data["agents"] if isinstance(x, dict)]
    return []


def harvest_agency() -> List[Dict[str, Any]]:
    imported = import_agency_agents(str(AGENCY_DIR))
    out: List[Dict[str, Any]] = []
    for item in imported:
        aid = str(item.get("id") or "")
        # Skip the meta "readme" persona that is just the upstream title card
        if aid in {"readme", "the-agency", "agency"}:
            continue
        tags = _ensure_tags(
            [str(t) for t in (item.get("tags") or [])],
            "agency",
            "agency-agents",
        )
        item = dict(item)
        item["tags"] = tags
        item["source"] = "agency-agents"
        # locate source_path relative to agents/agency
        stem = aid
        matches = list(AGENCY_DIR.rglob(f"*{stem}*.md"))
        if not matches:
            # try by role slug from filename stems
            matches = [p for p in AGENCY_DIR.rglob("*.md") if _slug_from_path(p) == aid]
        if matches:
            item["source_path"] = matches[0].relative_to(AGENCY_DIR).as_posix()
            # division = first path part
            div = matches[0].relative_to(AGENCY_DIR).parts[0]
            item["tags"] = _ensure_tags(item["tags"], div, "agency", "agency-agents")
            item["division"] = div
        out.append(item)
    return sorted(out, key=lambda x: str(x.get("id")))


def _slug_from_path(path: Path) -> str:
    stem = path.stem
    stem = re.sub(r"^(engineering|design|marketing|testing|sales|finance|product|support|specialized|academic|paid-media|project-management|spatial-computing|game)-", "", stem)
    return re.sub(r"[^a-zA-Z0-9]+", "-", stem.strip().lower()).strip("-")


def harvest_repo_agent_files() -> List[Dict[str, Any]]:
    """Pull other agent defs from agents/ (json / agent.md / agentx)."""
    out: Dict[str, Dict[str, Any]] = {}
    agents_root = ROOT / "agents"

    # markdown packs outside agency/
    for path in agents_root.rglob("*.md"):
        if "agency" in path.parts and path.parts[path.parts.index("agency")] == "agency":
            # agency handled separately
            if "agency" in path.parts[:3]:
                continue
        if path.name.lower() in {"readme.md", "tasks.md", "deployment-guide.md"}:
            continue
        if "node_modules" in path.parts:
            continue
        parsed = parse_markdown_agent(path)
        if not parsed:
            continue
        item = dict(parsed)
        tags = _ensure_tags([str(t) for t in (item.get("tags") or [])], "repo")
        # game / hive hints
        low = str(path).lower()
        if "hive" in low:
            tags = _ensure_tags(tags, "hive")
        if "game" in low:
            tags = _ensure_tags(tags, "game")
        item["tags"] = tags
        item["source"] = "repo-markdown"
        try:
            item["source_path"] = path.relative_to(agents_root).as_posix()
        except ValueError:
            item["source_path"] = str(path)
        out[str(item["id"])] = item

    # JSON agent objects
    for path in agents_root.rglob("*.json"):
        if path.name in {"package.json", "tsconfig.json", "access_profiles.json"}:
            continue
        if "agency_import" in path.name:
            continue
        if path.name == "agents.json" and path.parent.name == "agentx":
            continue  # destination
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows: List[Any]
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict) and "id" in data:
            rows = [data]
        elif isinstance(data, dict) and isinstance(data.get("agents"), list):
            rows = data["agents"]
        else:
            continue
        for row in rows:
            if not isinstance(row, dict) or not row.get("id"):
                continue
            item = dict(row)
            tags = _ensure_tags([str(t) for t in (item.get("tags") or [])], "repo")
            aid = str(item["id"])
            if aid in HIVE_IDS:
                tags = _ensure_tags(tags, "hive", "core")
            if aid in MULTI_IDS:
                tags = _ensure_tags(tags, "multi")
            item["tags"] = tags
            item.setdefault("source", "repo-json")
            try:
                item["source_path"] = path.relative_to(agents_root).as_posix()
            except ValueError:
                item["source_path"] = str(path)
            # don't clobber richer agency entries unless missing
            prev = out.get(aid)
            if prev and "agency" in (prev.get("tags") or []):
                continue
            out[aid] = item

    return sorted(out.values(), key=lambda x: str(x.get("id")))


def merge_registries(
    agency: List[Dict[str, Any]],
    repo: List[Dict[str, Any]],
    existing: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    for row in existing:
        if row.get("id"):
            by_id[str(row["id"])] = dict(row)
    for row in repo:
        aid = str(row.get("id") or "")
        if not aid:
            continue
        cur = by_id.get(aid, {})
        merged = {**cur, **row}
        merged["tags"] = _ensure_tags(
            list(cur.get("tags") or []) + list(row.get("tags") or [])
        )
        by_id[aid] = merged
    for row in agency:
        aid = str(row.get("id") or "")
        if not aid:
            continue
        cur = by_id.get(aid, {})
        merged = {**cur, **row}
        merged["tags"] = _ensure_tags(
            list(cur.get("tags") or []) + list(row.get("tags") or []),
            "agency",
            "agency-agents",
        )
        by_id[aid] = merged
    # ensure hive/multi tags on known cores
    for aid in HIVE_IDS:
        if aid in by_id:
            by_id[aid]["tags"] = _ensure_tags(list(by_id[aid].get("tags") or []), "hive", "core")
    for aid in MULTI_IDS:
        if aid in by_id:
            by_id[aid]["tags"] = _ensure_tags(list(by_id[aid].get("tags") or []), "multi")
    return sorted(by_id.values(), key=lambda x: str(x.get("id")))


def write_json(path: Path, payload: Any, dry_run: bool) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if dry_run:
        print(f"would_write {path} bytes={len(text.encode('utf-8'))}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path} bytes={path.stat().st_size}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    agency = harvest_agency()
    repo = harvest_repo_agent_files()
    existing = _load_json_list(AGENTX / "agents.json")
    merged = merge_registries(agency, repo, existing)

    agency_count = sum(1 for a in merged if "agency" in (a.get("tags") or []))
    hive_count = sum(1 for a in merged if "hive" in (a.get("tags") or []))
    multi_count = sum(1 for a in merged if "multi" in (a.get("tags") or []))

    write_json(AGENTX / "agency_import.json", agency, args.dry_run)
    write_json(AGENTX / "agents.json", merged, args.dry_run)
    if MIRROR.exists() or True:
        write_json(MIRROR / "agency_import.json", agency, args.dry_run)
        write_json(MIRROR / "agents.json", merged, args.dry_run)

    report = {
        "ok": True,
        "dry_run": bool(args.dry_run),
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "agency_md_imported": len(agency),
        "repo_harvested": len(repo),
        "registry_total": len(merged),
        "tagged_agency": agency_count,
        "tagged_hive": hive_count,
        "tagged_multi": multi_count,
        "paths": {
            "agency_dir": str(AGENCY_DIR),
            "agents_json": str(AGENTX / "agents.json"),
            "agency_import": str(AGENTX / "agency_import.json"),
        },
    }
    if not args.dry_run:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        LOG.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print("log", LOG)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
