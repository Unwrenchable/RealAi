"""
RealAI ability runner — catalog + execute via orchestrator honesty catalog / tools.

Abilities are first-class Hive surfaces (LIVE/PARTIAL/SOFT), not chat slash-tools.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def catalog(client, *, live_only: bool = False) -> Dict[str, Any]:
    data = client.capabilities()
    names = list(data.get("capabilities") or [])
    if live_only:
        names = [n for n in names if not str(n).startswith("partial:")]
    by_status = data.get("by_status") or (data.get("coverage") or {}).get("by_status") or {}
    return {
        "ok": True,
        "count": len(names),
        "capabilities": names,
        "by_status": by_status,
        "weighted_pct": data.get("weighted_pct"),
        "ability_count": data.get("ability_count"),
        "raw": data,
    }


def normalize_ability_name(name: str) -> str:
    n = (name or "").strip()
    if not n:
        raise ValueError("empty ability name")
    if n.startswith("ability."):
        return n
    # allow bare ids from catalog (chat_completion → ability.chat_completion)
    if n.startswith("partial:"):
        n = n.split(":", 1)[1]
    return f"ability.{n}"


def run_ability(
    client,
    name: str,
    *,
    input_text: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    tool = normalize_ability_name(name)
    args: Dict[str, Any] = {}
    if input_text:
        args["input"] = input_text
    if context:
        args["context"] = context
    result = client.tool_execute(tool, args)
    ok = True
    if isinstance(result, dict) and result.get("error"):
        ok = False
    return {"ok": ok, "ability": tool, "arguments": args, "result": result}


def list_tool_functions(client) -> Dict[str, Any]:
    data = client.tools()
    tools = data.get("tools") or []
    rows: List[Dict[str, Any]] = []
    for t in tools:
        if not isinstance(t, dict):
            continue
        fn = t.get("function") or {}
        rows.append(
            {
                "name": fn.get("name") or t.get("name"),
                "description": fn.get("description") or t.get("description") or "",
            }
        )
    return {"ok": True, "count": len(rows), "tools": rows, "raw": data}
