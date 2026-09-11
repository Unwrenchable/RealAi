#!/usr/bin/env python3
"""Wire / validate nextgen hive agents from .github/agents into Craft roster.

Detects overseer, coder, architect, analyst, memory, governor, router;
writes scan_results/HIVE_AGENTS.json; registers role->model routing.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "scan_results" / "HIVE_AGENTS.json"
ARCHETYPES = (
    "overseer",
    "coder",
    "architect",
    "analyst",
    "memory",
    "governor",
    "router",
)


def main() -> int:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from core.orchestration.hive_router import (
        ROLE_MODEL_TABLE,
        load_github_hive_agents,
        register_routes,
        route_model,
    )

    try:
        from realai.v3_runtime_bridge import hive_agents_status, list_agent_tools_agents
    except Exception as e:
        print(f"[wire_hive_agents] bridge import failed: {e}", flush=True)
        hive_agents_status = None
        list_agent_tools_agents = None

    agents = load_github_hive_agents()
    by_id = {str(a.get("id")): a for a in agents if a.get("id")}
    present = [a for a in ARCHETYPES if a in by_id]
    missing = [a for a in ARCHETYPES if a not in by_id]
    routes = register_routes()

    roster = None
    status = None
    if hive_agents_status is not None:
        status = hive_agents_status()
    if list_agent_tools_agents is not None:
        roster = list_agent_tools_agents(limit=20, query="hive")

    payload = {
        "ok": len(missing) == 0,
        "hive_mode": len(missing) == 0,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "path": ".github/agents",
        "required": list(ARCHETYPES),
        "present": present,
        "missing": missing,
        "count_json": len(agents),
        "role_models": dict(ROLE_MODEL_TABLE),
        "routing_sample": {r: route_model(r) for r in ARCHETYPES},
        "routes": {
            "hive_mode": routes.get("hive_mode"),
            "hive_agents": routes.get("hive_agents"),
            "fallback": routes.get("fallback"),
        },
        "bridge_status": status,
        "roster_preview": (roster or {}).get("agents") if isinstance(roster, dict) else None,
        "agents": [
            {
                "id": by_id[aid].get("id"),
                "role": by_id[aid].get("role"),
                "preferred_model": by_id[aid].get("preferred_model") or route_model(aid),
                "capabilities": (by_id[aid].get("capabilities") or [])[:8],
                "path": by_id[aid].get("_path"),
            }
            for aid in present
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"[wire_hive_agents] hive_mode={payload['hive_mode']} "
        f"present={len(present)}/{len(ARCHETYPES)} missing={missing}",
        flush=True,
    )
    print(f"[wire_hive_agents] wrote {OUT}", flush=True)
    for a in payload["agents"]:
        print(
            f"  - {a['id']}: model={a['preferred_model']} caps={a['capabilities'][:3]}",
            flush=True,
        )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
