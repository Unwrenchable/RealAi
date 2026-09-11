"""Bridge recovered long-term memory engines into core.memory."""
from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def load_long_term_engine():
    """Prefer promoted long_term_engine, else recovered primary-clean path."""
    try:
        from core.memory.long_term_engine import MemoryEngine  # type: ignore
        return MemoryEngine
    except Exception:
        pass
    # Dynamic path via registry
    try:
        from adapters import resolve_path
        for mid in (
            "primary-clean-2026-07-31-HOMEPC-p1c9e2",
            "recovery-primary-clean-20260731-clean",
            "unique-modules-2026-08-01-HOMEPC-u194c3",
        ):
            p = resolve_path(mid)
            if p and (p / "realai" / "memory" / "engine.py").exists():
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "recovered_memory_engine", p / "realai" / "memory" / "engine.py"
                )
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    return getattr(mod, "MemoryEngine", mod)
    except Exception:
        pass
    return None


def memory_capabilities() -> dict[str, Any]:
    return {
        "core_sqlite": True,
        "long_term_engine": load_long_term_engine() is not None,
        "summarizer": True,
    }
