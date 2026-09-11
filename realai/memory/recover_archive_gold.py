#!/usr/bin/env python3
"""
Curated archive GOLD recovery (idempotent).

Re-run safely: skips identical files. Never overwrites clean frontend/VS Code
clients. Memory snapshots go to recovered/ only — live DBs untouched.

Usage:
  python scanners/recover_archive_gold.py
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("REALAI_ROOT", r"C:\realai"))
RECOVERED = ROOT / "recovered" / "from_archive"
LOG: list = []


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_file(src: Path, dst: Path, reason: str) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    rel_src = str(src.relative_to(ROOT)).replace("\\", "/")
    rel_dst = str(dst.relative_to(ROOT)).replace("\\", "/")
    if dst.exists() and sha(src) == sha(dst):
        LOG.append({"action": "skip_identical", "src": rel_src, "dst": rel_dst, "reason": reason})
        return "skip"
    if dst.exists():
        bak = dst.with_suffix(dst.suffix + ".pre_recovery.bak")
        if not bak.exists():
            shutil.copy2(dst, bak)
    shutil.copy2(src, dst)
    LOG.append({
        "action": "copied",
        "src": rel_src,
        "dst": rel_dst,
        "sha256": sha(src),
        "size": src.stat().st_size,
        "reason": reason,
    })
    print(f"  + {rel_dst}")
    return "copied"


def main() -> int:
    if not ROOT.is_dir():
        print(f"ROOT missing: {ROOT}", file=sys.stderr)
        return 2

    print("=== UI clients ===")
    reg_src = ROOT / "archive/realai-clean/realai-core/ui/lib/registryClient.ts"
    chat_src = ROOT / "archive/realai-clean/realai-core/ui/lib/realaiClient.ts"
    if not reg_src.is_file():
        print("registryClient source missing — skip UI recovery", file=sys.stderr)
    else:
        for t in (
            ROOT / "packages/sdk-ts/src/registryClient.ts",
            ROOT / "realai/packages/sdk-ts/src/registryClient.ts",
            RECOVERED / "ui/registryClient.ts",
        ):
            copy_file(reg_src, t, "unique_registryClient")
        for t in (
            ROOT / "packages/sdk-ts/src/envChatClient.ts",
            ROOT / "realai/packages/sdk-ts/src/envChatClient.ts",
            RECOVERED / "ui/envChatClient.ts",
        ):
            copy_file(chat_src, t, "env_chat_client_GOLD")

    arch_fe = ROOT / "archive/realai-clean__dup1/realai-frontend__dup1/src/lib/realai.ts"
    arch_ty = ROOT / "archive/realai-clean__dup1/realai-frontend__dup1/src/lib/types.ts"
    if arch_fe.is_file():
        copy_file(arch_fe, RECOVERED / "ui/frontend_realai.historical.ts", "historical_only")
    if arch_ty.is_file():
        copy_file(arch_ty, RECOVERED / "ui/frontend_types.historical.ts", "historical_only")

    print("=== AgentX ===")
    ax_src = ROOT / "archive/agent-tools-main/.agentx"
    for dest in (ROOT / "agents/agentx", ROOT / "realai/agents/agentx", RECOVERED / "agentx"):
        for name in ("agents.json", "access_profiles.json", "agency_import.json", "README.md"):
            s = ax_src / name
            if s.is_file():
                copy_file(s, dest / name, "agentx")

    print("=== Memory snapshots ===")
    candidates = [
        (ROOT / "archive/logs_data/realai_memory.json", "json_interactions_6d542331"),
        (ROOT / "archive/real-fin/realai/realai/realai_memory.json", "json_0f5d57d1"),
        (ROOT / "archive/RealAIProject/realai/realai_memory.json", "json_30f4a985"),
        (ROOT / "archive/realai_repo/realai/realai_memory.json", "json_ab4dea6e"),
        (ROOT / "archive/real-fin/realai/realai_memory.db", "db_c4a80d2f"),
        (ROOT / "archive/realai-clean/realai_memory.sqlite3", "sqlite_c928866b"),
        (ROOT / "archive/RealAIProject/realai_memory.sqlite3", "sqlite_ca7e2000"),
        (ROOT / "archive/realai_sdk/realai_memory.sqlite3", "sqlite_bd99ea95"),
        (ROOT / "archive/utilities/realai_knowledge_store.json", "knowledge_store_208d4db4"),
    ]
    mem_index = []
    mem_root = RECOVERED / "memory_snapshots"
    for src, label in candidates:
        if not src.is_file():
            continue
        h = sha(src)[:12]
        dest = mem_root / f"{label}__{h}{src.suffix}"
        copy_file(src, dest, f"memory:{label}")
        mem_index.append({
            "label": label,
            "sha256": sha(src),
            "size": src.stat().st_size,
            "recovered_as": str(dest.relative_to(ROOT)).replace("\\", "/"),
            "source": str(src.relative_to(ROOT)).replace("\\", "/"),
        })
    mem_root.mkdir(parents=True, exist_ok=True)
    (mem_root / "INDEX.json").write_text(
        json.dumps({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "policy": "Snapshots only. Live DBs not replaced.",
            "snapshots": mem_index,
        }, indent=2),
        encoding="utf-8",
    )

    # SDK export wiring (idempotent)
    export_block = (
        "\n// Recovered from archive/ (GOLD contracts) — registry + env chat helpers\n"
        'export * from "./registryClient";\n'
        "export {\n"
        "  chatCompletion as envChatCompletion,\n"
        "  extractContent as envExtractContent,\n"
        "  type ChatMessage as EnvChatMessage,\n"
        "  type ChatCompletion as EnvChatCompletion,\n"
        "  type RealAIClientOptions as EnvChatClientOptions,\n"
        '} from "./envChatClient";\n'
    )
    for idx in (
        ROOT / "packages/sdk-ts/src/index.ts",
        ROOT / "realai/packages/sdk-ts/src/index.ts",
    ):
        if not idx.is_file():
            continue
        text = idx.read_text(encoding="utf-8")
        if 'from "./registryClient"' in text:
            continue
        bak = idx.with_suffix(".ts.pre_recovery.bak")
        if not bak.exists():
            shutil.copy2(idx, bak)
        idx.write_text(text.rstrip() + "\n" + export_block + "\n", encoding="utf-8")
        LOG.append({"action": "patched_sdk_index", "dst": str(idx.relative_to(ROOT)).replace("\\", "/")})
        print(f"  patched {idx.relative_to(ROOT)}")

    RECOVERED.mkdir(parents=True, exist_ok=True)
    summary = {
        "copied": sum(1 for a in LOG if a["action"] == "copied"),
        "skipped_identical": sum(1 for a in LOG if a["action"] == "skip_identical"),
        "patched": sum(1 for a in LOG if a["action"] == "patched_sdk_index"),
        "memory_snapshots": len(mem_index),
    }
    log_path = RECOVERED / "RECOVERY_LOG.json"
    log_path.write_text(
        json.dumps({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "policy": "curated_archive_recovery",
            "actions": LOG,
            "summary": summary,
        }, indent=2),
        encoding="utf-8",
    )
    shutil.copy2(log_path, ROOT / "scan_results" / "archive_recovery_log.json")
    print("SUMMARY", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
