#!/usr/bin/env python3
"""Restore remaining package-root modules from nested gold / quarantine (batch 3)."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "realai"
Q = ROOT / "_quarantine" / "realai"

# Multi-agent engine stays at realai.orchestration.orchestrator.
# Package-root orchestrator matches quarantine: scan/patch RealAIOrchestrator.
SHIMS = {
    "nested_realai_model_catalog.py": (
        "realai.models.nested_realai_model_catalog",
        "Nested model catalog facade",
    ),
    "orchestrator.py": (
        "realai.plugins.orchestrator",
        "Scan/patch RealAIOrchestrator (not the multi-agent engine)",
    ),
    "realai_gui.py": ("realai.ui.realai_gui", "Desktop GUI"),
    "realai_hive_orchestrator.py": (
        "realai.agents.realai_hive_orchestrator",
        "Hive orchestrator agent",
    ),
    "realai_self_heal.py": ("realai.agents.realai_self_heal", "Self-heal agent"),
    "realai__self_heal.py": ("realai.agents.realai__self_heal", "Self-heal agent alias"),
    "realai_self_healing_core.py": (
        "realai.core.realai_self_healing_core",
        "Self-healing core",
    ),
    "realai_self_improving_agent.py": (
        "realai.agents.realai_self_improving_agent",
        "Self-improving agent",
    ),
    "self_improving_agent.py": (
        "realai.agents.self_improving_agent",
        "Self-improving agent",
    ),
    "test_local_server.py": ("realai.tests.test_local_server", "Local server smoke test"),
    "test_realai.py": ("realai.tests.test_realai", "RealAI smoke test"),
}

# scripts/ is not an importable package — copy gold to package root.
COPIES = [
    "lambda_embeddings_audio.py",
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
