"""Named layers above/below Universe Mode (documentation constants only)."""
from __future__ import annotations

from typing import Any, Dict, List

LAYERS: List[str] = [
    "Universe Mode",
    "Dimensional Runtime",
    "Multi-Singularity Federation",
    "Quantum Layer",
    "Omniverse Mode",
]


def describe() -> Dict[str, Any]:
    return {
        "apex": LAYERS[0],
        "layers": list(LAYERS),
        "note": "Universe Mode unifies worlds; deeper layers are named placeholders until gold exists.",
    }