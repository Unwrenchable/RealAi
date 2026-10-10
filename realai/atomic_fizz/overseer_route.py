"""``model: realai-overseer`` fallback for chat endpoints.

There is no dedicated Overseer GGUF yet, so requests for ``realai-overseer``
(or ``overseer`` / ``overseer-77``) are served by the local default model with
the OVERSEER-77 persona prompt prepended. Status: PARTIAL (persona via prompt,
not a fine-tuned model). Set ``REALAI_OVERSEER_MODEL`` to a real model id to
forward that id upstream instead.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

OVERSEER_MODEL_IDS = {"realai-overseer", "overseer", "overseer-77", "realai-overseer-77"}


def is_overseer_model(model: Any) -> bool:
    return str(model or "").strip().lower() in OVERSEER_MODEL_IDS


def apply_overseer_persona(messages: List[Dict[str, Any]], model: Any) -> Tuple[List[Dict[str, Any]], Dict[str, Any] | None]:
    """Return ``(messages, meta)``; ``meta`` is ``None`` when not an overseer request."""
    if not is_overseer_model(model):
        return messages, None
    from realai.atomic_fizz.overseer_prompt import OVERSEER_SYSTEM_PROMPT

    msgs = list(messages or [])
    already = any(
        m.get("role") == "system" and "OVERSEER-77" in str(m.get("content") or "") for m in msgs
    )
    if not already:
        msgs = [{"role": "system", "content": OVERSEER_SYSTEM_PROMPT}] + msgs
    meta = {
        "requested_model": str(model),
        "served_by": os.environ.get("REALAI_OVERSEER_MODEL") or "local default model + OVERSEER-77 persona prompt",
        "status": "PARTIAL",
    }
    return msgs, meta
