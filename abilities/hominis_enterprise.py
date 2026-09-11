"""Backward-compatible alias → ability.hive_governance."""

from __future__ import annotations

from typing import Any

from abilities.hive_governance import ABILITY as _GOV  # noqa: F401
from abilities.hive_governance import run as _run

ABILITY = {
    **dict(_GOV),
    "id": "hominis_enterprise",
    "name": "hominis_enterprise",
    "dest": "abilities/hominis_enterprise.py",
    "status_note": "Alias of hive_governance (renamed)",
    "alias_of": "hive_governance",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    out = _run(input=input, context=context, **kwargs)
    if isinstance(out, dict):
        out = dict(out)
        out["ability"] = "hominis_enterprise"
        out["alias_of"] = "hive_governance"
        out["note"] = "Renamed to ability.hive_governance — prefer that id"
    return out
