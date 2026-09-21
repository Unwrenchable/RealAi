"""Live plugin authority for RealAI.

First-party plugins live as subpackages of ``realai.plugins``.
Root ``plugins/`` is a compat shim that aliases this package.

Older plugin internals still ``import plugins.rackup_coach``. Installing this
module also registers ``sys.modules['plugins']`` so those imports resolve to
the same gold without a second copy.

``_loader.py`` in this folder is a vendored Pydantic entry-point helper,
not the RealAI plugin host. Use ``load_first_party`` / ``register_all``.
"""
from __future__ import annotations

import sys
from importlib import import_module
from typing import Any

from . import sample_plugin

# Keep v2 import path alive: `import plugins.rackup_coach` == this package.
sys.modules.setdefault("plugins", sys.modules[__name__])

FIRST_PARTY = (
    "sample_plugin",
    "rackup_coach",
    "atomic_fizz_realai",
    "atomicfizz_coach",
)

__all__ = [
    "FIRST_PARTY",
    "sample_plugin",
    "list_first_party",
    "load_first_party",
    "register_all",
]


def list_first_party() -> list[str]:
    return list(FIRST_PARTY)


def load_first_party(name: str):
    """Import a first-party plugin module (package or module)."""
    if name == "sample_plugin":
        return sample_plugin
    return import_module(f"realai.plugins.{name}")


def register_all(model: Any = None, config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Call ``register(model, config)`` on every first-party plugin that has it."""
    registered: list[dict[str, Any]] = []
    cfg = config or {}
    for name in FIRST_PARTY:
        try:
            mod = load_first_party(name)
        except Exception as exc:
            registered.append({"name": name, "ok": False, "error": str(exc)})
            continue
        register = getattr(mod, "register", None)
        if not callable(register):
            registered.append({"name": name, "ok": True, "registered": False, "reason": "no register()"})
            continue
        try:
            meta = register(model, cfg.get(name) if isinstance(cfg.get(name), dict) else cfg)
            if not isinstance(meta, dict):
                meta = {"name": name, "ok": True}
            meta.setdefault("name", name)
            meta.setdefault("ok", True)
            registered.append(meta)
        except Exception as exc:
            registered.append({"name": name, "ok": False, "error": str(exc)})
    return registered
