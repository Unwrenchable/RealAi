"""transformers version shims for training/export.

``from_pretrained(dtype=...)`` replaced ``torch_dtype=`` in transformers 4.56 (``torch_dtype`` now logs a
deprecation warning). Older releases (the DirectML venv pins 4.44.x) do NOT reject an unknown ``dtype=``:
it is forwarded to the model config and the weights silently load in fp32. So the keyword is picked by
version, never by try/except.
"""
from __future__ import annotations

import re
from typing import Any, Dict

DTYPE_KW_MIN = (4, 56)


def _version_tuple(v: str) -> tuple:
    nums = [int(x) for x in re.findall(r"\d+", str(v))[:2]]
    return tuple(nums + [0] * (2 - len(nums)))


def dtype_kw_name(version: str = "") -> str:
    if not version:
        try:
            import transformers

            version = transformers.__version__
        except Exception:
            return "torch_dtype"
    return "dtype" if _version_tuple(version) >= DTYPE_KW_MIN else "torch_dtype"


def dtype_kwargs(dtype: Any, version: str = "") -> Dict[str, Any]:
    """{"dtype": dtype} on transformers >= 4.56, else {"torch_dtype": dtype}."""
    return {dtype_kw_name(version): dtype}
