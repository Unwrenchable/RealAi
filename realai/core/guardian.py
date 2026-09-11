"""
Synthetic Guardian Layer — tool policy for RealAI.

Mode via env REALAI_GUARDIAN_MODE:
  - advisory (default): log warnings, never block valid schema tools
  - hard_block: block dangerous / restricted tools unless explicitly allowed

Also honors payload / call-site flags when provided.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger("realai.guardian")

_HARD_BLOCK_LEVELS = frozenset({"dangerous"})
_RESTRICTED_BLOCK_IN_HARD = frozenset({"dangerous", "restricted"})


def guardian_mode() -> str:
    mode = os.environ.get("REALAI_GUARDIAN_MODE", "advisory").strip().lower()
    if mode in ("hard", "hard_block", "enforce", "strict"):
        return "hard_block"
    return "advisory"


def check_tool_call(
    tool_name: str,
    arguments: Optional[Dict[str, Any]],
    schema: Any,
) -> Dict[str, Any]:
    """
    Returns:
      allowed: bool
      mode: str
      warnings: list[str]
      errors: list[str]
      decision: allow | warn | block
    """
    arguments = arguments or {}
    mode = guardian_mode()
    safety = getattr(schema, "safety_level", "safe") or "safe"
    source = getattr(schema, "source", "builtin") or "builtin"
    status = getattr(schema, "ability_status", "") or ""

    warnings: list[str] = []
    errors: list[str] = []
    decision = "allow"

    # Catalog stubs / missing abilities
    if source == "ability_catalog" and status in ("MISSING", "STUB"):
        msg = f"ability {tool_name} is {status} — not a live effector"
        if mode == "hard_block":
            errors.append(msg)
            decision = "block"
        else:
            warnings.append(msg)
            decision = "warn"

    # Dangerous tools
    if safety == "dangerous":
        msg = f"tool {tool_name} is dangerous"
        if mode == "hard_block":
            errors.append(msg + " (REALAI_GUARDIAN_MODE=hard_block)")
            decision = "block"
        else:
            warnings.append(msg + " (advisory only)")
            decision = "warn"

    # Restricted tools in hard mode require confirmation flag
    if safety == "restricted" and mode == "hard_block":
        if not arguments.get("_confirmed") and not arguments.get("confirm"):
            errors.append(
                f"tool {tool_name} is restricted; pass confirm=true under hard_block mode"
            )
            decision = "block"

    allowed = decision != "block"
    if warnings:
        logger.info("guardian %s tool=%s warnings=%s", mode, tool_name, warnings)
    if errors:
        logger.warning("guardian %s tool=%s blocked errors=%s", mode, tool_name, errors)

    return {
        "allowed": allowed,
        "mode": mode,
        "decision": decision,
        "warnings": warnings,
        "errors": errors,
        "tool_name": tool_name,
        "safety_level": safety,
        "policy": (
            "advisory: never hard-blocks dangerous tools; logs warnings. "
            "Set REALAI_GUARDIAN_MODE=hard_block to enforce."
            if mode == "advisory"
            else "hard_block: blocks dangerous tools and unconfirmed restricted tools."
        ),
    }
