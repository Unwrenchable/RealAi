#!/usr/bin/env python3
"""
Assemble gold index + promote queue from EXISTING scan_results.

Phase 0-1 of RealAI v3 consolidation:
  - No full-repo re-walk
  - No multi-GB cavity JSON
  - Distill DDS-3 / deep gold / archive / abilities / models into one queue

Outputs:
  scan_results/gold_index.json
  scan_results/gold_index.md
  scan_results/promote_queue.json
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(os.environ.get("REALAI_ROOT", r"C:\realai"))
SCAN = ROOT / "scan_results"
ERA_MAP = SCAN / "era_map.json"
OUT_INDEX = SCAN / "gold_index.json"
OUT_MD = SCAN / "gold_index.md"
OUT_QUEUE = SCAN / "promote_queue.json"

SUBSYSTEMS = [
    "server_api",
    "agents_hive",
    "memory_rag",
    "tools_mcp",
    "self_improve_training",
    "providers_models",
    "ui_fusion_vscode",
    "cli_sdk",
    "world_npc",
    "web3_solana",
    "other",
]

NOISE_PARTS = {
    "node_modules", "venv", ".venv", ".vs", "build", "dist", "__pycache__",
    ".pytest_cache", ".next", "site-packages", "phase4_tools", "plan_phase4_preview",
    "scan_results", "terminals", ".blackbox", "chocolatey", ".git", ".eggs",
}

# path/token → subsystem
SUB_RULES: List[Tuple[str, re.Pattern]] = [
    ("server_api", re.compile(r"api_server|server/|/v1/|router\.|openai.?compat", re.I)),
    ("agents_hive", re.compile(r"agent|hive|orchestrat|planner|executor|persona|agentx", re.I)),
    ("memory_rag", re.compile(r"memory|rag|vector|embed|chroma|faiss|knowledge", re.I)),
    ("tools_mcp", re.compile(r"tool|mcp|plugin|manifest", re.I)),
    ("self_improve_training", re.compile(r"self_improv|self.reflect|finetun|training|lora|evolver|bootstrap", re.I)),
    ("providers_models", re.compile(r"provider|model_registry|gguf|llama|qwen|inference|backend", re.I)),
    ("ui_fusion_vscode", re.compile(r"frontend|fusion|vscode|webview|chatPanel|registryClient|realaiClient", re.I)),
    ("cli_sdk", re.compile(r"\bcli\b|sdk|package\.json", re.I)),
    ("world_npc", re.compile(r"worldmodel|world_model|npc|quest|overseer", re.I)),
    ("web3_solana", re.compile(r"solana|web3|anchor|wallet", re.I)),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[warn] failed to load {path}: {e}")
        return None


def norm_path(p: str) -> str:
    return p.replace("\\", "/").lstrip("./")


def is_noise_path(p: str) -> bool:
    parts = set(norm_path(p).lower().split("/"))
    return bool(parts & NOISE_PARTS) or any(n in norm_path(p).lower() for n in NOISE_PARTS)


def era_of(rel: str) -> str:
    r = norm_path(rel).lower()
    if r.startswith("realai_og_mess") or "/realai_og_mess/" in r:
        return "og_mess"
    if r.startswith("archive/") or "/archive/" in r:
        return "archive"
    if ".backup" in r or "historical_backup" in r:
        return "backup"
    if "__dup" in r or " copy" in r:
        return "duplicate"
    if r.startswith("recovered/"):
        return "recovered"
    if r.startswith("realai/") or r.startswith("apps/") or r.startswith("core/") or r.startswith("agents/"):
        return "clean"
    if r.startswith("models/"):
        return "models"
    if r.startswith("training/"):
        return "training"
    return "other"


def subsystem_of(text: str) -> str:
    for name, pat in SUB_RULES:
        if pat.search(text):
            return name
    return "other"


def authority_target(rel: str, sub: str) -> str:
    """Suggest canonical target under authority tree."""
    base = Path(norm_path(rel)).name
    mapping = {
        "server_api": f"realai/{base}",
        "agents_hive": f"agents/{base}",
        "memory_rag": f"realai/memory/{base}" if base.endswith(".py") else f"recovered/from_gold/{base}",
        "tools_mcp": f"realai/tools/{base}" if base.endswith(".py") else f"plugins/{base}",
        "self_improve_training": f"realai/{base}" if "self" in base.lower() else f"training/{base}",
        "providers_models": f"providers/{base}" if base.endswith((".ts", ".yaml", ".yml")) else f"realai/{base}",
        "ui_fusion_vscode": f"apps/frontend/src/lib/{base}" if base.endswith((".ts", ".tsx")) else f"apps/vscode/src/{base}",
        "cli_sdk": f"packages/sdk-ts/src/{base}" if base.endswith(".ts") else f"cli/{base}",
        "world_npc": f"realai/{base}",
        "web3_solana": f"realai/web3/{base}" if base.endswith(".py") else f"recovered/from_gold/{base}",
    }
    return mapping.get(sub, f"recovered/from_gold/{base}")


def priority_score(action: str, era: str, sub: str, reason: str) -> int:
    score = 50
    if action == "promote":
        score += 40
    elif action == "needs_review":
        score += 25
    elif action == "rewrite":
        score += 15
    elif action == "archive_only":
        score += 5
    else:
        score -= 20

    if era in ("archive", "og_mess"):
        score += 10
    if era == "backup":
        score += 5
    if era == "clean":
        score -= 30  # already authority-ish

    if sub in ("self_improve_training", "agents_hive", "server_api", "memory_rag"):
        score += 15
    if "only_outside" in reason or "unique" in reason or "recover" in reason:
        score += 20
    if "memory" in reason:
        score += 10
    return score


def add_candidate(
    bag: Dict[str, Dict[str, Any]],
    *,
    key: str,
    path: str,
    era: str,
    sub: str,
    reason: str,
    action: str,
    source: str,
    extra: Optional[Dict] = None,
) -> None:
    path = norm_path(path)
    if is_noise_path(path) and action != "skip_dup":
        action = "skip_dup"
        reason = f"noise_path:{reason}"

    if key in bag:
        # merge reasons / bump
        bag[key]["reasons"].append(f"{source}:{reason}")
        bag[key]["sources"].add(source)
        if action == "promote" and bag[key]["action"] != "promote":
            bag[key]["action"] = "promote"
        bag[key]["priority"] = max(bag[key]["priority"], priority_score(action, era, sub, reason))
        return

    bag[key] = {
        "id": key,
        "path": path,
        "era": era,
        "subsystem": sub,
        "action": action,
        "target": authority_target(path, sub),
        "reasons": [f"{source}:{reason}"],
        "sources": {source},
        "priority": priority_score(action, era, sub, reason),
        "extra": extra or {},
    }


def from_archive_triage(bag: Dict[str, Dict[str, Any]], data: Any) -> None:
    if not data:
        return
    for e in data.get("recover_candidates") or []:
        path = e.get("file") or e.get("path") or ""
        if not path:
            continue
        reason = e.get("reason") or e.get("class") or "archive_recover"
        action = "promote"
        if "duplicate" in str(reason):
            action = "skip_dup"
        elif "memory" in str(reason):
            action = "needs_review"  # don't auto-swap live DBs
        elif "same_name_different_hash" in str(reason):
            action = "needs_review"
        elif "historical" in str(reason) or "docs" in str(e.get("class", "")):
            action = "archive_only"
        sub = subsystem_of(path + " " + str(reason))
        if e.get("class") == "source_code":
            action = "promote" if action == "archive_only" else action
        add_candidate(
            bag,
            key=f"archive:{norm_path(path)}",
            path=path,
            era="archive",
            sub=sub,
            reason=str(reason),
            action=action,
            source="dds3_archive_triage",
            extra={"class": e.get("class"), "size": e.get("size")},
        )


def from_ability_inventory(bag: Dict[str, Dict[str, Any]], data: Any) -> None:
    if not data:
        return
    for e in (data.get("only_outside_clean") or [])[:500]:
        token = e.get("token") or ""
        files = e.get("sample_files") or []
        eras = e.get("eras") or ["other"]
        if not files:
            # token-only: stage under recovered capabilities
            path = f"capability:{token}"
            add_candidate(
                bag,
                key=f"ability:{token}",
                path=path,
                era=eras[0],
                sub=subsystem_of(token),
                reason="ability_only_outside_clean",
                action="needs_review",
                source="dds3_ability_inventory",
                extra={"token": token, "file_count": e.get("file_count")},
            )
            continue
        for f in files[:3]:
            add_candidate(
                bag,
                key=f"ability_file:{norm_path(f)}",
                path=f,
                era=era_of(f),
                sub=subsystem_of(f + " " + token),
                reason=f"ability_token:{token}",
                action="promote" if era_of(f) != "clean" else "skip_dup",
                source="dds3_ability_inventory",
                extra={"token": token},
            )


def from_deep_gold(bag: Dict[str, Dict[str, Any]], data: Any) -> None:
    if not data:
        return
    summary = data.get("summary") or data
    # only_outside_clean_top from summary
    for e in (summary.get("only_outside_clean_top") or [])[:200]:
        path = e.get("file") or ""
        if not path:
            continue
        groups = e.get("groups") or []
        sub = "other"
        for g in groups:
            mapped = {
                "models_inference": "providers_models",
                "agents_orchestrate": "agents_hive",
                "memory_rag": "memory_rag",
                "tools_mcp_plugins": "tools_mcp",
                "self_improve_training": "self_improve_training",
                "server_api_ui": "server_api",
                "world_npc_game": "world_npc",
                "web3_solana": "web3_solana",
            }.get(g)
            if mapped:
                sub = mapped
                break
        action = "needs_review"
        if "self_improve" in groups or "agents_orchestrate" in groups:
            action = "promote"
        if is_noise_path(path) or path.endswith((".md", ".txt")) and "self" not in path.lower():
            # docs: archive_only unless self/training/agent critical
            if not any(x in str(groups) for x in ("self_improve", "agents", "server_api")):
                action = "archive_only"
        add_candidate(
            bag,
            key=f"deep:{norm_path(path)}",
            path=path,
            era=e.get("era") or era_of(path),
            sub=sub,
            reason=f"deep_gold_outside_clean hits={e.get('hit_count')}",
            action=action,
            source="dds3_deep_gold_map",
            extra={"groups": groups, "hit_count": e.get("hit_count")},
        )

    # model-related docs sample — archive_only / review
    for path in (summary.get("model_related_docs") or [])[:50]:
        if is_noise_path(path):
            continue
        add_candidate(
            bag,
            key=f"modeldoc:{norm_path(path)}",
            path=path,
            era=era_of(path),
            sub="providers_models",
            reason="model_related_doc",
            action="archive_only" if era_of(path) != "clean" else "skip_dup",
            source="dds3_deep_gold_map",
        )


def from_missing_summary(bag: Dict[str, Dict[str, Any]], data: Any) -> None:
    if not data:
        return
    # top_missing refs — not files; map to needs_review capability holes
    for e in (data.get("top_missing") or [])[:80]:
        ref = e.get("reference") or ""
        if not ref or len(ref) < 3:
            continue
        # skip junk tokens
        if ref.lower() in {"type", "train", "dataset", "os", "json", "path"}:
            continue
        sub = subsystem_of(ref)
        add_candidate(
            bag,
            key=f"missing_ref:{ref}",
            path=f"missing:{ref}",
            era="other",
            sub=sub,
            reason=f"dds3_unique_missing count={e.get('count')}",
            action="needs_review",
            source="dds3_missing_files_summary",
            extra={"count": e.get("count")},
        )


def from_deep_models(bag: Dict[str, Dict[str, Any]], data: Any) -> None:
    if not data:
        return
    # real gguf only if any; stubs are assets already known
    for e in (data.get("real_gguf") or [])[:20]:
        path = e.get("path") or ""
        add_candidate(
            bag,
            key=f"gguf:{norm_path(path)}",
            path=path,
            era=e.get("era") or era_of(path),
            sub="providers_models",
            reason="real_gguf_asset",
            action="archive_only",  # path register, not code promote
            source="deep_model_inventory",
            extra={"size_mb": e.get("size_mb")},
        )
    # note stubs
    stubs = data.get("summary", {}).get("gguf_stub_lt_50mb") or 0
    if stubs:
        add_candidate(
            bag,
            key="meta:stub_gguf_notice",
            path="models/*.gguf_stubs",
            era="models",
            sub="providers_models",
            reason=f"{stubs}_stub_ggufs_use_real_weights_under_models_and_llama_vulkan",
            action="skip_dup",
            source="deep_model_inventory",
        )


def from_hardcoded_known_gold(bag: Dict[str, Dict[str, Any]]) -> None:
    """Known high-value items from prior recovery / machine map."""
    known = [
        ("recovered/from_archive/ui/registryClient.ts", "ui_fusion_vscode", "already_staged_registry_client", "skip_dup"),
        ("packages/sdk-ts/src/registryClient.ts", "cli_sdk", "already_in_authority", "skip_dup"),
        ("packages/sdk-ts/src/envChatClient.ts", "cli_sdk", "already_in_authority", "skip_dup"),
        ("agents/agentx/agents.json", "agents_hive", "already_promoted_agentx", "skip_dup"),
        ("realai/self_improvement.py", "self_improve_training", "authority_self_improve", "skip_dup"),
        ("C:/Users/tsmit/Downloads/realai_finetune_dataset.jsonl", "self_improve_training", "import_training_dataset", "promote"),
        ("C:/Users/tsmit/Downloads/agent_manifests_for_finetuning.json", "self_improve_training", "import_finetune_manifests", "promote"),
        ("archive/realai-clean/realai-core/ui/lib/registryClient.ts", "ui_fusion_vscode", "archive_unique_ui_client", "skip_dup"),
        ("C:/llama-vulkan/models/realai-1.0/weights/realai-1.0-instruct-Q4_K_M.gguf", "providers_models", "inference_asset", "archive_only"),
        ("C:/realai/models/qwen2.5-coder-7b-instruct-q5_k_m.gguf", "providers_models", "default_vulkan_model", "archive_only"),
    ]
    for path, sub, reason, action in known:
        era = era_of(path) if not path.startswith("C:") else ("secondary" if "Users" in path else "assets")
        if "Downloads" in path:
            era = "secondary_gold"
        target = "training/data/" + Path(path).name if "Downloads" in path and action == "promote" else authority_target(path, sub)
        key = f"known:{norm_path(path)}"
        add_candidate(
            bag,
            key=key,
            path=path,
            era=era,
            sub=sub,
            reason=reason,
            action=action,
            source="known_gold",
        )
        if key in bag and "Downloads" in path:
            bag[key]["target"] = target


def finalize(bag: Dict[str, Dict[str, Any]]) -> Tuple[List[Dict], Dict[str, List]]:
    items = []
    for v in bag.values():
        v = dict(v)
        v["sources"] = sorted(v["sources"])
        v["reasons"] = v["reasons"][:12]
        items.append(v)
    items.sort(key=lambda x: (-x["priority"], x["subsystem"], x["path"]))

    by_sub: Dict[str, List] = defaultdict(list)
    for it in items:
        by_sub[it["subsystem"]].append(it)
    return items, by_sub


def write_md(items: List[Dict], by_sub: Dict[str, List], meta: Dict) -> str:
    lines = []
    lines.append("# RealAI v3 Gold Index")
    lines.append("")
    lines.append(f"Generated: `{meta['generated_at']}`")
    lines.append("")
    lines.append("Distilled from existing scan_results (no full-repo re-walk).")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(f"- Total candidates: **{len(items)}**")
    act = Counter(i["action"] for i in items)
    for a, n in act.most_common():
        lines.append(f"- `{a}`: {n}")
    lines.append("")
    lines.append("## Promote queue (top 40)")
    lines.append("")
    lines.append("| Pri | Action | Subsystem | Path | Target |")
    lines.append("|-----|--------|-----------|------|--------|")
    for it in items[:40]:
        if it["action"] in ("skip_dup",):
            continue
        lines.append(
            f"| {it['priority']} | `{it['action']}` | {it['subsystem']} | `{it['path'][:70]}` | `{it['target'][:40]}` |"
        )
    # re-do including only promote/needs_review
    promo = [i for i in items if i["action"] in ("promote", "needs_review", "rewrite")][:40]
    lines.append("")
    lines.append("### Actionable only (promote / needs_review / rewrite)")
    lines.append("")
    for it in promo:
        lines.append(
            f"- **[{it['action']}]** `{it['path']}` → `{it['target']}`  \n"
            f"  _{it['reasons'][0] if it['reasons'] else ''}_"
        )
    lines.append("")
    lines.append("## By subsystem")
    lines.append("")
    for sub in SUBSYSTEMS:
        group = by_sub.get(sub) or []
        if not group:
            continue
        lines.append(f"### {sub} ({len(group)})")
        lines.append("")
        for it in group[:15]:
            lines.append(f"- `{it['action']}` · `{it['path'][:90]}`")
        if len(group) > 15:
            lines.append(f"- … {len(group) - 15} more")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("Next: review this file, then Phase 2 `promote_gold.py --dry-run` (not run yet).")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    print("[assemble] loading existing scan_results…")
    era = load_json(ERA_MAP)
    archive = load_json(SCAN / "dds3_archive_triage.json")
    abilities = load_json(SCAN / "dds3_ability_inventory.json")
    deep = load_json(SCAN / "dds3_deep_gold_map_summary.json") or load_json(SCAN / "dds3_deep_gold_map.json")
    missing = load_json(SCAN / "dds3_missing_files_summary.json")
    models = load_json(SCAN / "deep_model_inventory.json")

    bag: Dict[str, Dict[str, Any]] = {}
    from_hardcoded_known_gold(bag)
    from_archive_triage(bag, archive)
    from_ability_inventory(bag, abilities)
    from_deep_gold(bag, deep)
    from_missing_summary(bag, missing)
    from_deep_models(bag, models)

    items, by_sub = finalize(bag)
    meta = {
        "generated_at": utc_now(),
        "root": str(ROOT),
        "era_map_loaded": era is not None,
        "inputs": {
            "archive_triage": archive is not None,
            "ability_inventory": abilities is not None,
            "deep_gold": deep is not None,
            "missing_summary": missing is not None,
            "deep_models": models is not None,
        },
        "total_candidates": len(items),
        "by_action": dict(Counter(i["action"] for i in items)),
        "by_subsystem": {s: len(by_sub.get(s) or []) for s in SUBSYSTEMS},
    }

    # gold index
    index = {
        "meta": meta,
        "by_subsystem": {s: by_sub.get(s) or [] for s in SUBSYSTEMS},
        "all": items,
    }
    # promote queue: actionable ordered
    queue = {
        "meta": {
            **meta,
            "note": "Phase 2 will consume this. Do not apply until user review.",
        },
        "queue": [i for i in items if i["action"] in ("promote", "needs_review", "rewrite")],
    }

    SCAN.mkdir(parents=True, exist_ok=True)
    OUT_INDEX.write_text(json.dumps(index, indent=2, default=list), encoding="utf-8")
    OUT_QUEUE.write_text(json.dumps(queue, indent=2, default=list), encoding="utf-8")
    OUT_MD.write_text(write_md(items, by_sub, meta), encoding="utf-8")

    print(f"[assemble] -> {OUT_INDEX}")
    print(f"[assemble] -> {OUT_QUEUE}")
    print(f"[assemble] -> {OUT_MD}")
    print(f"[assemble] total={len(items)} actionable={len(queue['queue'])}")
    print("[assemble] by_action:", meta["by_action"])
    print("[assemble] top actionable:")
    for it in queue["queue"][:15]:
        print(f"  [{it['priority']}] {it['action']:12} {it['subsystem']:22} {it['path'][:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
