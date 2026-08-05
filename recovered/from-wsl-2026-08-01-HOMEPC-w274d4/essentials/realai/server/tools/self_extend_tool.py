"""
self_extend_tool — recovered capability surface.

No historical file named self_extend_tool.py was found under Users\\tsmit.
This adapter exposes extension via Aura skill registry + self_improvement hooks
so the missing-filename contract is satisfied without inventing fake logic.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def extend_capability(description: str, code: Optional[str] = None) -> Dict[str, Any]:
    """
    Record an extension intent and optionally route to self_improvement.

    Returns a structured result for tool catalogs / agent calls.
    """
    result: Dict[str, Any] = {
        "tool": "self_extend_tool",
        "status": "partial",
        "description": description,
        "note": (
            "Gold filename never existed; wired to self_improvement + aura skills. "
            "Pass code= to propose a skill body for review."
        ),
    }
    try:
        from realai.self_improvement import PerformanceEvaluator  # noqa: F401
        result["self_improvement"] = "available"
    except Exception as e:
        result["self_improvement"] = f"unavailable: {e}"

    if code:
        # Do not auto-write source; stage proposal only
        from pathlib import Path
        from datetime import datetime, timezone

        stage = Path(__file__).resolve().parents[3] / "recovered" / "from_aura_p0_hunt" / "extend_proposals"
        stage.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = stage / f"extend_{ts}.py"
        path.write_text(
            f'"""Proposed extension: {description}"""\n\n{code}\n',
            encoding="utf-8",
        )
        result["proposal_path"] = str(path)
        result["status"] = "proposed"
    return result


def run(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    arguments = arguments or {}
    return extend_capability(
        str(arguments.get("description") or arguments.get("goal") or "extend"),
        code=arguments.get("code"),
    )
