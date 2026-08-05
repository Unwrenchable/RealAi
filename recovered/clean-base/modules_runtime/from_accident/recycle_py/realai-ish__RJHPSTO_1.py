"""Compatibility shim for legacy imports.

Canonical config lives in realai/config.py.
"""

import warnings


def _warn_legacy_import() -> None:
    warnings.warn(
        "Deprecated import path: use 'from realai.config import Config, config' instead of 'from config import ...'.",
        FutureWarning,
        stacklevel=2,
    )


_warn_legacy_import()

from realai.config import Config, config

__all__ = ["Config", "config"]
