#!/usr/bin/env python3
"""Restore package-root shims/copies from nested gold / quarantine (batch 2)."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "realai"
Q = ROOT / "_quarantine" / "realai"

SHIMS = {
    "identity.py": ("realai.core.identity", "Identity layer"),
    "knowledge_graph.py": ("realai.memory.knowledge_graph", "Knowledge graph"),
    "safety.py": ("realai.core.safety", "Safety layer"),
    "audit.py": ("realai.core.audit", "Audit / observability"),
    "critique.py": ("realai.core.critique", "Critique engine"),
    "plugin_marketplace.py": ("realai.plugins.plugin_marketplace", "Plugin marketplace"),
    "server_settings.py": ("realai.server.server_settings", "Server settings"),
    "engine.py": ("realai.core.engine", "Core engine"),
    "nest_orchestrators.py": ("realai.orchestration.nest_orchestrators", "Nest orchestrators index"),
    "hive_orchestrator.py": ("realai.abilities.hive_orchestrator", "Hive orchestrator ability"),
    "realai_local_server.py": ("realai.server.realai_local_server", "Local server"),
    "unified_orchestrator.py": ("realai.core.unified_orchestrator", "Unified orchestrator"),
    "rise_system.py": ("realai.core.rise_system", "RISE self-improvement"),
    "supervisor.py": ("realai.core.supervisor", "Hierarchical supervisor"),
}

COPIES = [
    "recovery_registry.py",
    "self_heal_loop.py",
    "mcp_vault77.py",
    "coding_agent.py",
    "hierarchical_agent.py",
]

SHIM_TEMPLATE = '''"""Package-root import shim for {title}.

Gold lives at ``{target}`` after the 2026-08-30 package-root sort.
This module re-exports that gold. Do not put logic here.
"""
from __future__ import annotations

from {target} import *  # noqa: F403
'''


def main() -> int:
    created: list[tuple[str, str, str]] = []
    for name, (target, title) in SHIMS.items():
        dest = LIVE / name
        if dest.exists():
            print("skip exists", name)
            continue
        dest.write_text(SHIM_TEMPLATE.format(target=target, title=title), encoding="utf-8")
        created.append(("shim", name, target))
        print("shim", name, "->", target)

    for name in COPIES:
        dest = LIVE / name
        src = Q / name
        if dest.exists():
            print("skip exists", name)
            continue
        if not src.is_file():
            print("missing quarantine", name)
            continue
        shutil.copy2(src, dest)
        created.append(("copy", name, str(src)))
        print("copy", name)

    print("DONE", len(created))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
