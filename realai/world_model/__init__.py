"""realai.world_model -> the canonical module file realai/world_model.py (docs/CANONICAL_PATHS.md).

This directory is a dump of older copies (recovered/nested snapshots) and, being a package, shadows the canonical
realai/world_model.py. Rather than move anything, the package loads the canonical file by path and re-exports it.
Before 2026-10-17 it re-exported realai/world_model/world_model/world_model.py, which was byte-identical to the
canonical file at the time. See docs/BUILD_LEFTOVERS.md.
"""
import importlib.util as _ilu
import sys as _sys
from pathlib import Path as _Path

_name = "realai._world_model_canonical"
_mod = _sys.modules.get(_name)
if _mod is None:
    _spec = _ilu.spec_from_file_location(_name, _Path(__file__).resolve().parent.parent / "world_model.py")
    _mod = _ilu.module_from_spec(_spec)
    _sys.modules[_name] = _mod  # dataclasses need the module registered while executing
    _spec.loader.exec_module(_mod)  # type: ignore[union-attr]
for _k, _v in vars(_mod).items():
    if not _k.startswith("__"):
        globals()[_k] = _v
__all__ = list(getattr(_mod, "__all__", [k for k in vars(_mod) if not k.startswith("_")]))
