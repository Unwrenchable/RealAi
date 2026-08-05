"""
Recovery registry — maps kilo-era recovered assets into live RealAI paths.

Does not bulk-merge; exposes inventory + promote helpers used by orchestrator
GET /v1/recovery and scripts/promote_kilo_recovery.py.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_PKG = Path(__file__).resolve().parent
_ROOT = _PKG.parent
_STAGE = _ROOT / "recovered" / "from_kilo_restore"
_DISCOVERED = _STAGE / "_discovered"
_SCAN = _ROOT / "scan_results"

# Prefer worktree full weights; staged copy is configs-only + pointer
LORA_CANDIDATES = [
    Path(os.environ.get("USERPROFILE", r"C:\Users\tsmit"))
    / ".grok"
    / "worktrees"
    / "tsmit-realai"
    / "realai2"
    / "checkpoints_lora",
    Path("/mnt/c/Users/tsmit/.grok/worktrees/tsmit-realai/realai2/checkpoints_lora"),
    _DISCOVERED / "checkpoints_lora",
]

REALAI2_CANDIDATES = [
    Path(os.environ.get("USERPROFILE", r"C:\Users\tsmit"))
    / ".grok"
    / "worktrees"
    / "tsmit-realai"
    / "realai2",
    Path("/mnt/c/Users/tsmit/.grok/worktrees/tsmit-realai/realai2"),
]


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_lora_root() -> Optional[Path]:
    for p in LORA_CANDIDATES:
        if p.is_dir() and any(p.iterdir()):
            return p
    return None


def resolve_realai2() -> Optional[Path]:
    for p in REALAI2_CANDIDATES:
        if p.is_dir():
            return p
    return None


def list_lora_adapters(limit: int = 200) -> List[Dict[str, Any]]:
    root = resolve_lora_root()
    if not root:
        return []
    out: List[Dict[str, Any]] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        cfg = child / "adapter_config.json"
        weights = child / "adapter_model.safetensors"
        if not cfg.is_file() and not weights.is_file():
            # nested checkpoint dirs (e.g. qwen.../checkpoint-4)
            for sub in child.iterdir() if child.is_dir() else []:
                if sub.is_dir() and (sub / "adapter_config.json").is_file():
                    out.append(_lora_entry(sub, root))
            continue
        out.append(_lora_entry(child, root))
        if len(out) >= limit:
            break
    return out[:limit]


def _lora_entry(path: Path, root: Path) -> Dict[str, Any]:
    cfg_path = path / "adapter_config.json"
    meta: Dict[str, Any] = {}
    if cfg_path.is_file():
        try:
            meta = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            meta = {}
    w = path / "adapter_model.safetensors"
    size = w.stat().st_size if w.is_file() else 0
    name = path.name
    return {
        "id": f"realai-lora-{name}".replace(" ", "-").lower()[:80],
        "name": name,
        "path": str(path),
        "relative": str(path.relative_to(root)) if str(path).startswith(str(root)) else name,
        "has_adapter_config": cfg_path.is_file(),
        "has_weights": w.is_file(),
        "weights_bytes": size,
        "base_model_name_or_path": meta.get("base_model_name_or_path"),
        "peft_type": meta.get("peft_type") or meta.get("peft_type"),
        "r": meta.get("r"),
        "role": "lora_adapter",
        "owned_by": "realai",
    }


def inventory() -> Dict[str, Any]:
    """Full recovery inventory for API + ops."""
    lora_root = resolve_lora_root()
    r2 = resolve_realai2()
    adapters = list_lora_adapters()
    staged_p0 = []
    p0 = _DISCOVERED / "realai2_p0"
    if p0.is_dir():
        staged_p0 = [str(p.relative_to(p0)) for p in p0.rglob("*") if p.is_file()]

    desktop_map = _SCAN / "desktop_missing_gold_map.json"
    desktop_summary = None
    if desktop_map.is_file():
        try:
            dm = json.loads(desktop_map.read_text(encoding="utf-8"))
            desktop_summary = {
                "hits": dm.get("hit_count"),
                "staged": dm.get("staged_count"),
                "p0_found": len(dm.get("p0_found_on_desktop_scan") or []),
                "p0_live_miss": dm.get("p0_missing_from_live_realai_pkg"),
                "map": str(desktop_map),
                "stage_dir": dm.get("stage_dir"),
            }
        except Exception as e:
            desktop_summary = {"error": str(e)}

    live_modules = {
        "lambda_embeddings_audio": (_PKG / "lambda_embeddings_audio.py").is_file(),
        "providers.local_llama": (_PKG / "providers" / "local_llama.py").is_file(),
        "server.embeddings_backend": (_PKG / "server" / "embeddings_backend.py").is_file(),
        "server.orchestration": (_PKG / "server" / "orchestration.py").is_file(),
        "server.tools_runtime": (_PKG / "server" / "tools_runtime.py").is_file(),
        "realai_agent_pkg": (_PKG / "realai_agent").is_dir() or (_ROOT / "realai_agent").is_dir(),
        "agent_runtime": (_PKG / "agent_runtime.py").is_file(),
        "world_model": (_PKG / "world_model.py").is_file(),
        "self_improvement": (_PKG / "self_improvement.py").is_file(),
        "desktop_agentx": (_ROOT / "recovered" / "from_desktop_missing" / "desktop_agentx").is_dir(),
        "desktop_fizz": (_ROOT / "recovered" / "from_desktop_missing" / "fizzRecovery").is_dir(),
    }

    return {
        "updated_at": _utc(),
        "stage_dir": str(_STAGE),
        "discovered_dir": str(_DISCOVERED),
        "realai2_root": str(r2) if r2 else None,
        "lora_root": str(lora_root) if lora_root else None,
        "lora_adapter_count": len(adapters),
        "lora_adapters_sample": adapters[:15],
        "staged_p0_files": staged_p0,
        "desktop_missing_gold": desktop_summary,
        "desktop_roots": [
            r"C:\Users\tsmit\OneDrive\Desktop",
            r"C:\Users\tsmit\Desktop",
            r"C:\Users\tsmit\Documents",
            r"C:\Users\tsmit\Downloads",
            r"C:\Users\tsmit\realai-clean",
            r"C:\Users\tsmit\realai",
            r"C:\Users\tsmit\realai_historical_backups",
            r"C:\Users\tsmit\backups",
            r"C:\Users\tsmit\Documents\GitHub\realai",
        ],
        "live_modules": live_modules,
        "live_modules_ready": sum(1 for v in live_modules.values() if v),
        "live_modules_total": len(live_modules),
        "kilo_forensics": str(_SCAN / "kilo_forensics.md"),
        "still_missing_report": str(_SCAN / "kilo_still_missing_report.md"),
        "endpoints": {
            "embeddings": "POST /v1/embeddings",
            "audio_transcription": "POST /v1/audio/transcriptions",
            "audio_speech": "POST /v1/audio/speech",
            "recovery": "GET /v1/recovery",
            "lora": "GET /v1/lora",
            "self_heal_discover_desktop": "POST /v1/self-heal/discover {\"mode\":\"desktop\"}",
            "local_llama_health": "via realai.providers.local_llama.local_llama_health",
        },
    }


def promote_core(dry_run: bool = False) -> Dict[str, Any]:
    """
    Promote high-value recovered packs into live tree without overwriting
    larger/better existing modules.
    """
    actions: List[Dict[str, Any]] = []
    p0 = _DISCOVERED / "realai2_p0"

    def _copy_if_better(src: Path, dest: Path, force_missing: bool = True) -> None:
        if not src.is_file():
            actions.append({"src": str(src), "dest": str(dest), "action": "skip_missing_src"})
            return
        if dest.is_file() and dest.stat().st_size >= src.stat().st_size and not force_missing:
            actions.append({
                "src": str(src),
                "dest": str(dest),
                "action": "keep_live_larger",
                "live_size": dest.stat().st_size,
                "src_size": src.stat().st_size,
            })
            return
        if dest.is_file() and force_missing is False:
            # only fill gaps unless explicitly new file
            if dest.stat().st_size > 0:
                actions.append({"src": str(src), "dest": str(dest), "action": "skip_exists"})
                return
        if dry_run:
            actions.append({"src": str(src), "dest": str(dest), "action": "would_copy"})
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        actions.append({"src": str(src), "dest": str(dest), "action": "copied", "bytes": dest.stat().st_size})

    # Do NOT overwrite adapted local modules with raw Lambda stubs.
    # Only seed lambda_embeddings_audio if completely missing.
    dest_emb = _PKG / "lambda_embeddings_audio.py"
    if not dest_emb.is_file():
        _copy_if_better(p0 / "lambda_embeddings_audio.py", dest_emb, force_missing=True)
    else:
        actions.append({
            "dest": str(dest_emb),
            "action": "keep_adapted_local",
            "note": "local v3 handler; raw Lambda stub stays in recovered/",
        })
    # Prefer fixed local_llama — only seed if missing
    if not (_PKG / "providers" / "local_llama.py").is_file():
        _copy_if_better(p0 / "providers" / "local_llama.py", _PKG / "providers" / "local_llama.py")

    # realai_agent package
    agent_src = _DISCOVERED / "realai_agent_from_desktop"
    agent_dest = _PKG / "realai_agent"
    if agent_src.is_dir() and not agent_dest.is_dir():
        if dry_run:
            actions.append({"src": str(agent_src), "dest": str(agent_dest), "action": "would_copytree"})
        else:
            shutil.copytree(agent_src, agent_dest)
            actions.append({"src": str(agent_src), "dest": str(agent_dest), "action": "copytree"})
    elif agent_dest.is_dir():
        actions.append({"dest": str(agent_dest), "action": "exists"})

    # policy / sanity for agent-tools-main
    for name in ("policy.json", "sanity_check.py"):
        src = p0 / "agent-tools-main" / name
        dest = _ROOT / "agent-tools-main" / name
        _copy_if_better(src, dest, force_missing=True)

    # Write inventory snapshot
    inv = inventory()
    inv_path = _SCAN / "recovery_inventory.json"
    if not dry_run:
        _SCAN.mkdir(parents=True, exist_ok=True)
        inv_path.write_text(json.dumps(inv, indent=2), encoding="utf-8")
        # lora catalog for model facade
        lora_path = _SCAN / "lora_adapters.json"
        lora_path.write_text(
            json.dumps(
                {
                    "updated_at": _utc(),
                    "root": inv.get("lora_root"),
                    "adapters": list_lora_adapters(limit=500),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    actions.append({"inventory": str(inv_path), "action": "wrote" if not dry_run else "would_write"})

    return {
        "ok": True,
        "dry_run": dry_run,
        "actions": actions,
        "inventory": inv if not dry_run else None,
    }


if __name__ == "__main__":
    import sys
    dry = "--dry-run" in sys.argv
    print(json.dumps(promote_core(dry_run=dry), indent=2, default=str))
