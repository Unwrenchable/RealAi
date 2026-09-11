"""Compat shim — authority is repo-root ``agent_tools`` (not ``realai.agent_tools``)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SHADOW = Path(__file__).resolve()
_ROOT = _SHADOW.parents[2]
_AUTH_INIT = _ROOT / "agent_tools" / "__init__.py"
_AUTH_DIR = _ROOT / "agent_tools"


def _load_authority():
    root_s = str(_ROOT)
    if root_s in sys.path:
        sys.path.remove(root_s)
    sys.path.insert(0, root_s)

    existing = sys.modules.get("agent_tools")
    existing_file = Path(getattr(existing, "__file__", "") or "")
    try:
        if existing is not None and existing_file.resolve() == _AUTH_INIT.resolve():
            return existing
    except Exception:
        pass

    # Clear shadow / partial modules so subpackages resolve under product root
    for key in list(sys.modules):
        if key == "agent_tools" or key.startswith("agent_tools."):
            mod = sys.modules.get(key)
            mod_file = Path(getattr(mod, "__file__", "") or "")
            try:
                under_shadow = str(mod_file).startswith(str(_SHADOW.parent))
            except Exception:
                under_shadow = False
            if key == "agent_tools" or under_shadow or mod is None:
                del sys.modules[key]

    if not _AUTH_INIT.is_file():
        raise ImportError(f"authority agent_tools missing: {_AUTH_INIT}")

    spec = importlib.util.spec_from_file_location(
        "agent_tools",
        _AUTH_INIT,
        submodule_search_locations=[str(_AUTH_DIR)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load agent_tools from {_AUTH_INIT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["agent_tools"] = module
    spec.loader.exec_module(module)
    return module


_auth = _load_authority()
sys.modules[__name__] = _auth
sys.modules["agent_tools"] = _auth
