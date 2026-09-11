"""Wide hunt: agents/abilities/tools across local user roots vs live RealAI."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOTS = [
    Path(r"C:\Users\tsmit\unique-hash-logs"),
    Path(r"C:\Users\tsmit\voicelab"),
    Path(r"C:\Users\tsmit\agent_tools_"),
    Path(r"C:\Users\tsmit\agent-tools"),
    Path(r"C:\Users\tsmit\agent-tools-main"),
    Path(r"C:\Users\tsmit\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS"),
    Path(r"C:\Users\tsmit\autoSkip"),
    Path(r"C:\Users\tsmit\cookbook"),
    Path(r"C:\Users\tsmit\EditPro"),
    Path(r"C:\Users\tsmit\effective-engine-main"),
    Path(r"C:\Users\tsmit\overseer-bot-ai"),
    Path(r"C:\Users\tsmit\overseer-bot-ai-main"),
    Path(r"C:\Users\tsmit\overseer-bot-ui"),
    Path(r"C:\Users\tsmit\overseerold"),
    Path(r"C:\Users\tsmit\projects"),
    Path(r"C:\Users\tsmit\Rack_em_up"),
    Path(r"C:\Users\tsmit\realai"),
    Path(r"C:\Users\tsmit\realai_documents"),
    Path(r"C:\Users\tsmit\realai_file_map"),
    Path(r"C:\Users\tsmit\realai_folder_map"),
    Path(r"C:\Users\tsmit\realai_historical_backups"),
    Path(r"C:\Users\tsmit\speedRouter-main"),
    Path(r"C:\Users\tsmit\supreme-goggles"),
    Path(r"C:\Users\tsmit\test-ledger"),
]

LIVE_HOME = Path(r"C:\RealAI-clean")
OUT = LIVE_HOME / "scan_results" / "WIDE_HUNT_ABILITIES_AGENTS.json"
OUT_MD = LIVE_HOME / "docs" / "sessions" / "WIDE_HUNT_LEARN.md"

SKIP_DIR = {
    "node_modules",
    ".git",
    ".next",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv",
    ".turbo",
    "coverage",
    ".cache",
    "rocksdb",
    "snapshots",
}

AGENT_NAME_RE = re.compile(
    r"(?i)(?:^|[/\\])(?:agents?|abilities?)[/\\][^/\\]+\.(?:md|json|agentx|py|ts|js)$"
)
INTERESTING_NAME = re.compile(
    r"(?i)(abilit|agent|skill|tool.?regist|orchestr|overseer|hive|rackup|voice|persona|workflow)"
)
ABILITY_ID_RE = re.compile(r'["\']id["\']\s*:\s*["\']([a-z0-9_\-]+)["\']')
AGENT_FRONT_RE = re.compile(r"(?im)^name:\s*(.+)$")


def load_live_ids() -> tuple[set[str], set[str]]:
    agents: set[str] = set()
    abilities: set[str] = set()
    ap = LIVE_HOME / "realai" / "agents" / "agentx" / "agents.json"
    if ap.is_file():
        data = json.loads(ap.read_text(encoding="utf-8"))
        for a in data if isinstance(data, list) else data.get("agents") or []:
            if isinstance(a, dict) and a.get("id"):
                agents.add(str(a["id"]).lower())
    try:
        from realai.ability_catalog import build_catalog

        cat = build_catalog()
        for a in cat.get("abilities") or []:
            if a.get("id"):
                abilities.add(str(a["id"]).lower())
    except Exception:
        pass
    # also ability module stems
    abdir = LIVE_HOME / "abilities"
    if abdir.is_dir():
        for p in abdir.glob("*.py"):
            abilities.add(p.stem.lower())
    return agents, abilities


def walk_interesting(root: Path, limit_files: int = 8000) -> dict:
    hits = {
        "root": str(root),
        "exists": root.exists(),
        "agent_files": [],
        "ability_files": [],
        "skill_files": [],
        "workflow_files": [],
        "interesting": [],
        "ids_found": [],
        "names_found": [],
        "errors": [],
    }
    if not root.exists():
        return hits

    n = 0
    for dirpath, dirnames, filenames in root.walk(top_down=True):
        # prune
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR and not d.startswith(".")]
        for fn in filenames:
            n += 1
            if n > limit_files:
                hits["errors"].append(f"file_cap_reached:{limit_files}")
                return hits
            p = Path(dirpath) / fn
            rel = str(p.relative_to(root)).replace("\\", "/")
            low = rel.lower()
            kind = None
            if "/agents/" in f"/{low}" or low.endswith(".agentx") or low.endswith(".agent.json") or low.endswith(".agent.md"):
                kind = "agent_files"
            elif "/abilities/" in f"/{low}" or "ability_" in low or low.endswith("abilities.json"):
                kind = "ability_files"
            elif "/skills/" in f"/{low}" or low.endswith("skill.md"):
                kind = "skill_files"
            elif "workflow" in low and low.endswith((".json", ".md", ".yaml", ".yml")):
                kind = "workflow_files"
            elif INTERESTING_NAME.search(fn) or INTERESTING_NAME.search(rel):
                kind = "interesting"
            else:
                continue

            entry = {"path": rel, "bytes": p.stat().st_size if p.is_file() else 0}
            hits[kind].append(entry)

            # light parse for ids/names
            if p.suffix.lower() in {".json", ".md", ".agentx", ".py"} and p.stat().st_size < 2_000_000:
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")[:80_000]
                except Exception:
                    continue
                if p.suffix.lower() == ".json" or "agents.json" in low or "abilities" in low:
                    for m in ABILITY_ID_RE.findall(text):
                        hits["ids_found"].append({"id": m, "from": rel})
                if p.suffix.lower() == ".md":
                    m = AGENT_FRONT_RE.search(text)
                    if m:
                        hits["names_found"].append({"name": m.group(1).strip(), "from": rel})
                    # stem as slug candidate
                    stem = p.stem
                    if stem and not stem.lower().startswith("readme"):
                        hits["ids_found"].append({"id": stem.lower().replace(" ", "-"), "from": rel, "kind": "stem"})
    return hits


def main() -> None:
    live_agents, live_abilities = load_live_ids()
    per_root = []
    novel_agent_ids: dict[str, list[str]] = defaultdict(list)
    novel_ability_ids: dict[str, list[str]] = defaultdict(list)
    learn_docs: list[dict] = []

    for root in ROOTS:
        print(f"scan {root} ...", flush=True)
        # deeper for high-value roots
        cap = 12000 if any(
            x in str(root).lower()
            for x in ("atomic", "agent_tools", "agent-tools", "overseer", "rack", "realai", "voicelab", "cookbook")
        ) else 4000
        h = walk_interesting(root, limit_files=cap)
        per_root.append(h)
        for item in h.get("ids_found") or []:
            iid = str(item.get("id") or "").lower().strip()
            if not iid or len(iid) < 3:
                continue
            src = f"{root.name}/{item.get('from')}"
            if iid in live_abilities or iid in live_agents:
                continue
            # classify by path
            fr = str(item.get("from") or "").lower()
            if "abilit" in fr:
                novel_ability_ids[iid].append(src)
            elif "agent" in fr or item.get("kind") == "stem":
                novel_agent_ids[iid].append(src)
            else:
                novel_agent_ids[iid].append(src)

        # docs of interest
        for bucket in ("interesting", "ability_files", "agent_files"):
            for e in h.get(bucket) or []:
                rel = e["path"]
                if rel.lower().endswith((".md", ".txt")) and any(
                    k in rel.lower() for k in ("abilit", "agent", "architect", "status", "contract", "wire", "learn")
                ):
                    learn_docs.append({"root": root.name, "path": rel, "bytes": e.get("bytes")})

    # prioritize novel
    def top_novel(d: dict[str, list[str]], n: int = 80):
        items = sorted(d.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        return [{"id": k, "sources": v[:5], "source_count": len(v)} for k, v in items[:n]]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "live_agents": len(live_agents),
        "live_abilities": len(live_abilities),
        "roots_scanned": len(ROOTS),
        "per_root_summary": [
            {
                "root": h["root"],
                "agent_files": len(h.get("agent_files") or []),
                "ability_files": len(h.get("ability_files") or []),
                "skill_files": len(h.get("skill_files") or []),
                "workflow_files": len(h.get("workflow_files") or []),
                "interesting": len(h.get("interesting") or []),
                "ids_found": len(h.get("ids_found") or []),
                "errors": h.get("errors") or [],
            }
            for h in per_root
        ],
        "novel_agent_ids": top_novel(novel_agent_ids, 120),
        "novel_ability_ids": top_novel(novel_ability_ids, 80),
        "learn_docs": learn_docs[:80],
        "high_value_roots": [],
    }

    # score roots
    for h in per_root:
        score = (
            len(h.get("agent_files") or []) * 3
            + len(h.get("ability_files") or []) * 4
            + len(h.get("skill_files") or []) * 2
            + len(h.get("workflow_files") or [])
            + min(len(h.get("ids_found") or []), 200)
        )
        report["high_value_roots"].append({"root": h["root"], "score": score})
    report["high_value_roots"].sort(key=lambda x: -x["score"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # markdown
    lines = [
        "# Wide hunt — abilities / agents / learn",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Live RealAI: **{report['live_agents']} agents**, **{report['live_abilities']} abilities**",
        "",
        "## Highest-value local roots",
        "",
    ]
    for r in report["high_value_roots"][:12]:
        lines.append(f"- score **{r['score']}** — `{r['root']}`")
    lines += ["", "## Novel agent ids (not in live registry)", ""]
    for a in report["novel_agent_ids"][:40]:
        lines.append(f"- `{a['id']}` ×{a['source_count']} — {a['sources'][0]}")
    lines += ["", "## Novel ability-ish ids", ""]
    for a in report["novel_ability_ids"][:30]:
        lines.append(f"- `{a['id']}` ×{a['source_count']} — {a['sources'][0]}")
    lines += ["", "## Docs worth reading / learning", ""]
    for d in report["learn_docs"][:25]:
        lines.append(f"- `{d['root']}/{d['path']}` ({d['bytes']} B)")
    lines += [
        "",
        "## Suggested promote order",
        "",
        "1. **ATOMIC-FIZZ** — game/overseer/media agents + grok media paths (local-first already preferred)",
        "2. **overseer-bot-*** — overseer UI/AI patterns for Hive governance",
        "3. **Rack_em_up** — rackup domain abilities already partially live",
        "4. **voicelab** — voice UX patterns for Console/Fusion",
        "5. **agent_tools_** — already largely merged; mine remaining skills/workflows only",
        "6. **cookbook / EditPro / supreme-goggles** — product-specific agents if not duplicates",
        "",
        f"Full JSON: `{OUT}`",
        "",
    ]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print("wrote", OUT)
    print("wrote", OUT_MD)
    print("novel_agents", len(report["novel_agent_ids"]), "novel_abilities", len(report["novel_ability_ids"]))


if __name__ == "__main__":
    main()
