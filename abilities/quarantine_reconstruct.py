import json
import shutil
import hashlib
from pathlib import Path
from typing import Dict, List, Any

ROOT = Path(r"C:\RealAI-clean")
QUARANTINE = ROOT / "_quarantine"
DELTA_ROOT = ROOT / "recovered" / "delta_candidates"
REPORT_PATH = ROOT / "recovered" / "reconstruction_report.json"
ABILITIES_INDEX_PATH = ROOT / "recovered" / "reconstruction_abilities_index.json"

CATEGORIES = {
    "abilities": ["abilities", "ability_", "ability"],
    "agents": ["agents", "agent_", "agentx"],
    "agent_tools": ["agent_tools"],
    "core": ["core"],
    "orchestrator": ["orchestrator", "router"],
    "plugins": ["plugins"],
    "personas": ["persona", "personas"],
    "world_model": ["world_model"],
    "promote": ["promote", "promotion"],
    "self_heal": ["self_heal", "heal"],
    "repo_walk": ["walk_root", "repo_organizer", "realai_root_walker"],
    "training": ["training", "datasets"],
    "experimental": ["experimental", "experimental_"],
    "unknown": [],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(path: Path) -> str:
    rel = path.relative_to(ROOT)
    rel_str = str(rel).lower()
    for cat, hints in CATEGORIES.items():
        for h in hints:
            if h in rel_str:
                return cat
    return "unknown"


def find_live_target(rel: Path) -> Path:
    parts = list(rel.parts)
    if parts and parts[0] == "_quarantine":
        parts[0] = "realai"
    return ROOT / Path(*parts)


def walk_quarantine() -> List[Path]:
    if not QUARANTINE.exists():
        return []
    return [p for p in QUARANTINE.rglob("*.py")]


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Ability entry — stage quarantine deltas (never auto-merge into live)."""
    ctx = dict(context or {})
    ctx.update(kwargs)
    # Default to status: full reconstruct walks/hashes all of _quarantine and can
    # take minutes. Explicit action=reconstruct (or input=reconstruct) required.
    raw_action = ctx.get("action")
    if raw_action is None or str(raw_action).strip() == "":
        raw_action = (input or "").strip() or "status"
    action = str(raw_action).strip().lower() or "status"
    if action in {"status", "info", "ok", "ping"}:
        return {
            "ok": True,
            "ability": "quarantine_reconstruct",
            "quarantine_exists": QUARANTINE.exists(),
            "quarantine": str(QUARANTINE),
            "delta_root": str(DELTA_ROOT),
            "report_path": str(REPORT_PATH),
            "note": "Pass action=reconstruct to stage deltas; merge stays interactive/CLI-only",
        }
    report = reconstruct()
    return {
        "ok": True,
        "ability": "quarantine_reconstruct",
        "action": "reconstruct",
        "total_files": report.get("total_files"),
        "delta_root": report.get("delta_root"),
        "report_path": str(REPORT_PATH),
        "abilities_index": str(ABILITIES_INDEX_PATH),
        "note": "Staged only — live merge requires explicit CLI confirmation",
    }


def reconstruct() -> Dict[str, Any]:
    DELTA_ROOT.mkdir(parents=True, exist_ok=True)

    findings: List[Dict[str, Any]] = []
    abilities_index: Dict[str, Dict[str, Any]] = {}

    for q_path in walk_quarantine():
        rel = q_path.relative_to(ROOT)
        category = classify(q_path)
        live_target = find_live_target(rel)

        delta_target = DELTA_ROOT / category / live_target.relative_to(ROOT)
        delta_target.parent.mkdir(parents=True, exist_ok=True)

        live_exists = live_target.exists()
        q_hash = sha256(q_path)
        live_hash = sha256(live_target) if live_exists and live_target.is_file() else None

        missing_in_live = not live_exists
        different = live_exists and live_hash != q_hash

        item = {
            "category": category,
            "quarantine_path": str(q_path),
            "live_target": str(live_target),
            "delta_target": str(delta_target),
            "missing_in_live": missing_in_live,
            "different_from_live": bool(different),
            "quarantine_sha256": q_hash,
            "live_sha256": live_hash,
        }
        findings.append(item)

        if missing_in_live or different:
            shutil.copy2(q_path, delta_target)

        # Abilities index: any file under abilities/ or named like an ability
        rel_str = str(rel).lower()
        if "abilities" in rel_str or "ability_" in rel_str:
            ability_id = q_path.stem
            entry = abilities_index.setdefault(
                ability_id,
                {
                    "id": ability_id,
                    "category": category,
                    "quarantine_paths": [],
                    "live_targets": [],
                    "delta_targets": [],
                },
            )
            entry["quarantine_paths"].append(str(q_path))
            entry["live_targets"].append(str(live_target))
            entry["delta_targets"].append(str(delta_target))

    report = {
        "root": str(ROOT),
        "quarantine_root": str(QUARANTINE),
        "delta_root": str(DELTA_ROOT),
        "total_files": len(findings),
        "findings": findings,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    with ABILITIES_INDEX_PATH.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "root": str(ROOT),
                "quarantine_root": str(QUARANTINE),
                "delta_root": str(DELTA_ROOT),
                "abilities": list(abilities_index.values()),
            },
            f,
            indent=2,
        )

    return report


def merge_with_confirmation(report: Dict[str, Any]) -> None:
    print("=== Quarantine Reconstruction Report ===")
    print(f"Total staged files: {report['total_files']}")
    print(f"Delta root: {report['delta_root']}")
    print(f"Report: {REPORT_PATH}")
    print(f"Abilities index: {ABILITIES_INDEX_PATH}")
    print()
    print("Merge mode: ASK BEFORE APPLY")
    ans = input("Apply reconstructed files into live tree? [y/N]: ").strip().lower()
    if ans != "y":
        print("Merge aborted. Staged files remain in delta_candidates.")
        return

    for item in report["findings"]:
        delta = Path(item["delta_target"])
        live = Path(item["live_target"])
        if not delta.exists():
            continue
        live.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(delta, live)
    print("Merge complete.")


def main():
    report = reconstruct()
    merge_with_confirmation(report)


if __name__ == "__main__":
    main()
