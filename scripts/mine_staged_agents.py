#!/usr/bin/env python3
"""Mine staged realai_orchestration / realai_agent into agents/ + realai/agents/.

Most gold bodies already live under modules/orchestrators, realai/orchestration,
and realai/core/agents. This script:
  - copies unique docs
  - adds RealAI-named packages (agents/orchestration, agents/hierarchical)
  - adds thin entrypoint shims (does not overwrite rich gold or intentional shims)

  python scripts/mine_staged_agents.py --dry-run
  python scripts/mine_staged_agents.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

LIVE = Path(__file__).resolve().parents[1]
STAGED_ORCH = LIVE / "recovered" / "from_d_roots" / "realai_orchestration"
STAGED_AGENT = LIVE / "recovered" / "from_d_roots" / "realai_agent"
LOG = LIVE / "docs" / "recovery" / "2026-09-19-mine-agents-orchestration.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def copy_unique(src: Path, dest: Path, dry_run: bool, results: List[Dict[str, Any]]) -> None:
    rec: Dict[str, Any] = {"src": str(src), "dest": str(dest)}
    if not src.is_file():
        rec.update(ok=False, action="missing_src")
        results.append(rec)
        return
    if dest.exists():
        same = sha(src) == sha(dest)
        rec.update(
            ok=True,
            action="skip_same" if same else "skip_exists",
            size_src=src.stat().st_size,
            size_dest=dest.stat().st_size,
        )
        results.append(rec)
        return
    if dry_run:
        rec.update(ok=True, action="would_copy", size=src.stat().st_size)
        results.append(rec)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    rec.update(ok=True, action="copied", size=dest.stat().st_size)
    results.append(rec)


def write_new(path: Path, content: str, dry_run: bool, results: List[Dict[str, Any]]) -> None:
    rec: Dict[str, Any] = {"dest": str(path)}
    if path.exists():
        old = path.read_text(encoding="utf-8", errors="replace")
        if old == content:
            rec.update(ok=True, action="skip_same")
        else:
            rec.update(ok=True, action="skip_exists", size=path.stat().st_size)
        results.append(rec)
        return
    if dry_run:
        rec.update(ok=True, action="would_write", size=len(content.encode("utf-8")))
        results.append(rec)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    rec.update(ok=True, action="written", size=path.stat().st_size)
    results.append(rec)


ORCH_INIT = '''"""RealAI orchestration agents package.

Canonical implementation lives in ``modules.orchestrators`` / ``realai.orchestration``.
This package exists so ``agents.orchestration`` imports resolve cleanly.
"""
from __future__ import annotations

try:
    from modules.orchestrators import *  # noqa: F403
except Exception:  # pragma: no cover
    from realai.orchestration import *  # type: ignore  # noqa: F403

__all__ = [name for name in globals() if not name.startswith("_")]
'''

HIER_MAIN = '''"""RealAI hierarchical agent main entry (gold: realai.core.agents)."""
from __future__ import annotations

from realai.core.agents.hierarchical_main import *  # noqa: F403
'''

HIER_TEST = '''"""Tests for RealAI hierarchical agents (gold: realai.core.agents)."""
from __future__ import annotations

from realai.core.agents.test_hierarchical_agent import *  # noqa: F403
'''

HIER_PKG = '''"""RealAI hierarchical multi-agent system.

Gold bodies: ``realai.core.agents`` (rise_system, supervisor, hierarchical_agent, …).
Top-level ``agents.rise_system`` / ``agents.supervisor`` remain shims into core.
"""
from __future__ import annotations

from realai.core.agents.hierarchical_agent import HierarchicalAgentSystem, hierarchical_agent
from realai.core.agents.rise_system import RISESystem
from realai.core.agents.supervisor import SupervisorAgent, AgentState

try:
    from realai.core.agents.hierarchical_main import *  # noqa: F403
except Exception:  # pragma: no cover
    pass

__all__ = [
    "HierarchicalAgentSystem",
    "hierarchical_agent",
    "RISESystem",
    "SupervisorAgent",
    "AgentState",
]
'''

TRAINING = '''"""RealAI agent training pipeline (gold: realai.core.agents.training_pipeline)."""
from __future__ import annotations

from realai.core.agents.training_pipeline import *  # noqa: F403
'''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dry = bool(args.dry_run)
    results: List[Dict[str, Any]] = []

    # Orchestration docs into gold homes
    copy_unique(STAGED_ORCH / "README.md", LIVE / "modules" / "orchestrators" / "README.md", dry, results)
    copy_unique(STAGED_ORCH / "README.md", LIVE / "realai" / "orchestration" / "README.md", dry, results)

    # RealAI-named orchestration packages
    write_new(LIVE / "agents" / "orchestration" / "__init__.py", ORCH_INIT, dry, results)
    write_new(LIVE / "realai" / "agents" / "orchestration" / "__init__.py", ORCH_INIT, dry, results)

    # Hierarchical entrypoints + package
    write_new(LIVE / "agents" / "hierarchical_main.py", HIER_MAIN, dry, results)
    write_new(LIVE / "realai" / "agents" / "hierarchical_main.py", HIER_MAIN, dry, results)
    write_new(LIVE / "agents" / "test_hierarchical_agent.py", HIER_TEST, dry, results)
    write_new(LIVE / "realai" / "agents" / "test_hierarchical_agent.py", HIER_TEST, dry, results)
    write_new(LIVE / "agents" / "hierarchical" / "__init__.py", HIER_PKG, dry, results)
    write_new(LIVE / "realai" / "agents" / "hierarchical" / "__init__.py", HIER_PKG, dry, results)
    write_new(LIVE / "agents" / "training_pipeline.py", TRAINING, dry, results)
    write_new(LIVE / "realai" / "agents" / "training_pipeline.py", TRAINING, dry, results)

    # Staged agent README + smaller tools module under hierarchical package
    copy_unique(STAGED_AGENT / "README.md", LIVE / "agents" / "hierarchical" / "README.md", dry, results)
    copy_unique(STAGED_AGENT / "README.md", LIVE / "realai" / "agents" / "hierarchical" / "README.md", dry, results)
    copy_unique(STAGED_AGENT / "tools.py", LIVE / "agents" / "hierarchical" / "tools.py", dry, results)
    copy_unique(STAGED_AGENT / "tools.py", LIVE / "realai" / "agents" / "hierarchical" / "tools.py", dry, results)

    report = {
        "ok": all(r.get("ok") for r in results),
        "dry_run": dry,
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "copied": sum(1 for r in results if r.get("action") in {"copied", "written"}),
        "would": sum(1 for r in results if str(r.get("action", "")).startswith("would_")),
        "skipped": sum(1 for r in results if str(r.get("action", "")).startswith("skip")),
        "inventory": {
            "orchestration_bodies": "already identical in modules/orchestrators + realai/orchestration",
            "agent_bodies": "already in realai/core/agents (rise_system/supervisor/hierarchical_*)",
            "agents_shims_kept": ["agents/rise_system.py", "agents/supervisor.py"],
            "packages_added": [
                "agents/orchestration",
                "realai/agents/orchestration",
                "agents/hierarchical",
                "realai/agents/hierarchical",
            ],
        },
        "results": results,
    }
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in report if k != "results"}, indent=2))
    for r in results:
        print(f"  {r.get('action'):12s} {r.get('dest')}")
    print("log", LOG)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
