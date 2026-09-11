#!/usr/bin/env python3
"""Curated nested quarantine / gold wiring (batch 4).

- Root ``aura/`` + ``adapters/`` packages (allowlist / GOOD_CODE_ROOTS)
- Fill ``realai/orchestration/{agent,pipeline}.py`` from core gold
- Promote hierarchical ``training_pipeline`` (+ entry/test) into core/agents
- Thin ability wraps for plugin tools still unwired
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "realai"
Q = ROOT / "_quarantine"

ABILITY_TEMPLATE = '''"""Thin wrap over ``{source}``."""

from __future__ import annotations

import importlib
from typing import Any

ABILITY = {{
    "id": "{ability_id}",
    "name": "{ability_id}",
    "type": "ability",
    "status": "CODE",
    "source": "{source}",
    "dest": "abilities/{ability_id}.py",
    "capabilities": {capabilities!r},
    "secrets_policy": "none",
}}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {{}})
    ctx.update(kwargs)
    mod = importlib.import_module("{source}")
    if hasattr(mod, "run"):
        result = mod.run(input=input, context=ctx, **kwargs)
    elif hasattr(mod, "main"):
        result = {{
            "main": True,
            "hint": "CLI module — invoke via python -m or pass argv in context",
            "exports": [n for n in dir(mod) if not n.startswith("_")][:40],
        }}
    else:
        result = {{
            "module": "{source}",
            "exports": [n for n in dir(mod) if not n.startswith("_")][:40],
        }}
    return {{"ok": True, "ability": "{ability_id}", "source": "{source}", "result": result}}
'''


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print("write", path.relative_to(ROOT))


def _copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    print("copy", src.relative_to(ROOT), "->", dest.relative_to(ROOT))


def wire_root_package(name: str, live_pkg: Path) -> None:
    dest = ROOT / name
    if dest.exists():
        print("skip root pkg exists", name)
        return
    dest.mkdir(parents=True, exist_ok=True)
    _write(
        dest / "__init__.py",
        f'"""Root shim package for ``{name}`` → ``realai.{name}``."""\n'
        "from __future__ import annotations\n\n"
        f"from realai.{name} import *  # noqa: F403\n",
    )
    # Re-export each top-level module file as a shim for allowlist paths like aura/memory.py
    for py in live_pkg.glob("*.py"):
        if py.name == "__init__.py":
            continue
        mod = py.stem
        _write(
            dest / py.name,
            f'"""Root shim for ``{name}.{mod}`` → ``realai.{name}.{mod}``."""\n'
            "from __future__ import annotations\n\n"
            f"from realai.{name}.{mod} import *  # noqa: F403\n",
        )


def main() -> int:
    # 1) Root packages expected by curated allowlist / GOOD_CODE_ROOTS
    wire_root_package("aura", LIVE / "aura")
    wire_root_package("adapters", LIVE / "adapters")

    # 2) Complete realai.orchestration with gold agent/pipeline/memory
    for name in ("agent.py", "pipeline.py", "memory.py"):
        src = LIVE / "core" / "orchestration" / name
        dest = LIVE / "orchestration" / name
        if dest.exists():
            print("skip exists", dest.relative_to(ROOT))
            continue
        if src.is_file():
            _copy(src, dest)
        else:
            qsrc = Q / "orchestration_gold" / name
            if qsrc.is_file():
                _copy(qsrc, dest)

    # Expand orchestration __init__ exports without breaking voice routing
    orch_init = LIVE / "orchestration" / "__init__.py"
    text = orch_init.read_text(encoding="utf-8")
    if "BaseAgent" not in text:
        orch_init.write_text(
            text.rstrip()
            + "\n\ntry:\n"
            + "    from .agent import BaseAgent\n"
            + "    from .pipeline import Pipeline\n"
            + '    __all__ += ["BaseAgent", "Pipeline"]\n'
            + "except Exception:  # optional gold surface\n"
            + "    pass\n",
            encoding="utf-8",
        )
        print("update", orch_init.relative_to(ROOT))

    # 3) Hierarchical gold leftovers → core/agents
    hier_q = Q / "hierarchical_agent_gold"
    hier_dest = LIVE / "core" / "agents"
    mapping = {
        "training_pipeline.py": "training_pipeline.py",
        "main.py": "hierarchical_main.py",  # avoid colliding with other main.py
        "test_agent.py": "test_hierarchical_agent.py",
    }
    for src_name, dest_name in mapping.items():
        src = hier_q / src_name
        dest = hier_dest / dest_name
        if not src.is_file():
            print("missing", src)
            continue
        if dest.exists():
            print("skip exists", dest.relative_to(ROOT))
            continue
        _copy(src, dest)

    # 4) Thin abilities for plugin tools not yet wrapped
    abilities = [
        (
            "code_engineer_cli",
            "realai.plugins.tools.code_engineer_cli",
            ["code_engineer", "patch", "cli"],
        ),
        (
            "harden_repos",
            "realai.plugins.tools.harden_repos",
            ["repos", "harden", "security"],
        ),
        (
            "rollout_all_repos",
            "realai.plugins.tools.rollout_all_repos",
            ["repos", "rollout", "web3"],
        ),
    ]
    for ability_id, source, caps in abilities:
        body = ABILITY_TEMPLATE.format(
            ability_id=ability_id,
            source=source,
            capabilities=caps,
        )
        for base in (ROOT / "abilities", LIVE / "abilities"):
            dest = base / f"{ability_id}.py"
            if dest.exists():
                print("skip exists", dest.relative_to(ROOT))
                continue
            _write(dest, body)

    print("DONE batch4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
