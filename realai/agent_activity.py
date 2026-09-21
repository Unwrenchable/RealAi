"""RealAI agent activity bus + graph helpers (ported from agent-tools dashboard).

Used by Hive to power ``/agents-ui/`` live visualization and SSE feed.
"""
from __future__ import annotations

import json
import os
import queue
import random
import threading
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

_PKG = Path(__file__).resolve().parent
_REPO = _PKG.parent

PROFILES_CANDIDATES = [
    _PKG / "agents" / "agentx" / "access_profiles.json",
    _REPO / "agents" / "agentx" / "access_profiles.json",
]

# Live Hive core roles (must be graph nodes so Agents UI can light them up).
HIVE_CORE_AGENTS: List[Dict[str, Any]] = [
    {
        "id": "overseer",
        "role": "Hive Overseer",
        "description": "Hive governance / Vault77-style oversight for RealAI local stack.",
        "tags": ["hive", "core", "governance"],
        "capabilities": ["oversight", "governance", "routing"],
        "required_tools": ["hive_run", "overseer"],
        "preferred_profile": "power",
        "risk_level": "high",
    },
    {
        "id": "coder",
        "role": "Hive Coder",
        "description": "Primary implementation agent for repo patches and tool runs.",
        "tags": ["hive", "core", "code"],
        "capabilities": ["code", "tools", "workspace"],
        "required_tools": ["workspace_list", "execute_code", "craft_run"],
        "preferred_profile": "balanced",
        "risk_level": "medium",
    },
    {
        "id": "architect",
        "role": "Hive Architect",
        "description": "Design / structure decisions across RealAI surfaces.",
        "tags": ["hive", "core", "design"],
        "capabilities": ["architecture", "planning"],
        "required_tools": ["workspace_list", "ability_coverage"],
        "preferred_profile": "balanced",
        "risk_level": "medium",
    },
    {
        "id": "analyst",
        "role": "Hive Analyst",
        "description": "Review, critique, and evidence gathering.",
        "tags": ["hive", "core", "analysis"],
        "capabilities": ["analysis", "review"],
        "required_tools": ["web_research", "workspace_grep"],
        "preferred_profile": "safe",
        "risk_level": "low",
    },
    {
        "id": "memory",
        "role": "Hive Memory",
        "description": "Memory / embeddings / recall for the local hive.",
        "tags": ["hive", "core", "memory"],
        "capabilities": ["memory", "embeddings"],
        "required_tools": ["workspace_read"],
        "preferred_profile": "safe",
        "risk_level": "low",
    },
    {
        "id": "governor",
        "role": "Hive Governor",
        "description": "Policy / safety gate for hive actions.",
        "tags": ["hive", "core", "policy"],
        "capabilities": ["governance", "policy"],
        "required_tools": ["self_heal_status"],
        "preferred_profile": "safe",
        "risk_level": "medium",
    },
    {
        "id": "router",
        "role": "Hive Router",
        "description": "Routes tasks to nest orchestrators and agent roles.",
        "tags": ["hive", "core", "routing"],
        "capabilities": ["routing", "orchestration"],
        "required_tools": ["hive_run", "multi_agent_run"],
        "preferred_profile": "balanced",
        "risk_level": "medium",
    },
    # Multi-agent pipeline aliases emitted on /v1/multi-agent/run + agents/run
    {
        "id": "researcher",
        "role": "Multi Researcher",
        "description": "Pipeline researcher role used by multi-agent runs.",
        "tags": ["hive", "multi"],
        "capabilities": ["research", "analysis"],
        "required_tools": [],
        "preferred_profile": "safe",
        "risk_level": "low",
    },
    {
        "id": "creative",
        "role": "Multi Creative",
        "description": "Pipeline creative role used by multi-agent runs.",
        "tags": ["hive", "multi"],
        "capabilities": ["creative", "planning"],
        "required_tools": [],
        "preferred_profile": "balanced",
        "risk_level": "low",
    },
    {
        "id": "executor",
        "role": "Multi Executor",
        "description": "Pipeline executor role used by multi-agent runs.",
        "tags": ["hive", "multi"],
        "capabilities": ["execution", "code"],
        "required_tools": [],
        "preferred_profile": "balanced",
        "risk_level": "medium",
    },
    {
        "id": "critic",
        "role": "Multi Critic",
        "description": "Pipeline critic role used by multi-agent runs.",
        "tags": ["hive", "multi"],
        "capabilities": ["review", "critique"],
        "required_tools": [],
        "preferred_profile": "safe",
        "risk_level": "low",
    },
    {
        "id": "hive-orchestrator",
        "role": "Hive Orchestrator",
        "description": "Top-level hive orchestrator for Agents UI runs.",
        "tags": ["hive", "core", "orchestration"],
        "capabilities": ["orchestration", "routing", "multi"],
        "required_tools": ["multi_agent_run", "hive_run"],
        "preferred_profile": "power",
        "risk_level": "high",
    },
]


def with_hive_core(agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Prepend live Hive roles so graph/SSE activations have nodes to attach to."""
    existing = {str(a.get("id") or "") for a in (agents or [])}
    merged: List[Dict[str, Any]] = []
    for core in HIVE_CORE_AGENTS:
        cid = str(core.get("id") or "")
        if cid and cid not in existing:
            merged.append(dict(core))
    merged.extend(list(agents or []))
    return merged


WORKFLOWS: List[Dict[str, Any]] = [
    {
        "name": "Feature Development",
        "color": "#7c5cfc",
        "steps": [
            "api-designer",
            "backend-engineer",
            "frontend-developer",
            "qa-engineer",
            "documentation-specialist",
        ],
    },
    {
        "name": "Security Review",
        "color": "#ff7b7b",
        "steps": ["cybersecurity-expert", "capability-guardian", "devsecops-engineer"],
    },
    {
        "name": "Hive Pipeline",
        "color": "#3ddc97",
        "steps": ["overseer", "router", "architect", "coder", "analyst", "governor", "memory"],
    },
    {
        "name": "Multi-Agent Pipeline",
        "color": "#7af0ff",
        "steps": ["hive-orchestrator", "researcher", "coder", "creative", "executor", "critic"],
    },
    {
        "name": "Game Production",
        "color": "#ff2bd6",
        "steps": [
            "game-creative-director",
            "game-designer",
            "gameplay-programmer",
            "game-qa-lead",
            "game-producer",
        ],
    },
    {
        "name": "Self-Improve",
        "color": "#39ff14",
        "steps": ["ai-self-builder", "meta-agent-engineer", "agent-evals-engineer", "feedback-learning-engineer"],
    },
]

_TASK_DESCRIPTIONS = [
    "analysing code structure",
    "reviewing security posture",
    "implementing feature logic",
    "running test suite",
    "drafting API schema",
    "generating documentation",
    "orchestrating sub-agents",
    "hive reflection cycle",
    "scanning for vulnerabilities",
    "coordinating cross-agent handoff",
    "grounding claims against repo",
    "evaluating agent quality",
]


class EventBus:
    """Thread-safe fan-out for SSE subscribers."""

    def __init__(self) -> None:
        self._subscribers: List[queue.Queue] = []
        self._lock = threading.Lock()
        self._history: List[Dict[str, Any]] = []
        self._history_max = 100
        self._active: Dict[str, Dict[str, Any]] = {}

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=80)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    def publish(self, event: Dict[str, Any]) -> None:
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._history_max:
                self._history = self._history[-self._history_max :]
            et = event.get("type")
            aid = str(event.get("agent_id") or "")
            if et == "dispatch" and aid:
                self._active[aid] = event
            elif et == "complete" and aid:
                self._active.pop(aid, None)
            dead: List[queue.Queue] = []
            for q in self._subscribers:
                try:
                    q.put_nowait(event)
                except queue.Full:
                    dead.append(q)
            for q in dead:
                try:
                    self._subscribers.remove(q)
                except ValueError:
                    pass

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history[-limit:])

    def active(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._active.values())


BUS = EventBus()
# Demo sim is OFF by default — Agents UI should show real hive/tool work first.
# Toggle via POST /v1/agents/simulation {"toggle": true}.
# Opt in with REALAI_AGENTS_SIM=1/true/on. Default is OFF.
_simulation_enabled = os.environ.get("REALAI_AGENTS_SIM", "0").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
_sim_started = False
_sim_lock = threading.Lock()


def load_profiles() -> List[Dict[str, Any]]:
    for p in PROFILES_CANDIDATES:
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except Exception:
                continue
    return [
        {"name": "safe", "write": False, "network": False},
        {"name": "balanced", "write": True, "network": False},
        {"name": "power", "write": True, "network": True},
    ]


def normalize_agent(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": raw.get("id") or raw.get("name") or "unknown",
        "role": raw.get("role") or raw.get("name") or raw.get("id") or "agent",
        "description": raw.get("description") or "",
        "tags": list(raw.get("tags") or []),
        "capabilities": list(raw.get("capabilities") or []),
        "required_tools": list(raw.get("required_tools") or []),
        "preferred_profile": raw.get("preferred_profile") or "balanced",
        "risk_level": raw.get("risk_level") or "medium",
    }


def build_graph(agents: List[Dict[str, Any]]) -> Dict[str, Any]:
    nodes = [normalize_agent(a) for a in agents]
    by_id = {n["id"]: n for n in nodes}
    seen: set[str] = set()
    edges: List[Dict[str, Any]] = []

    for i, a in enumerate(nodes):
        for b in nodes[i + 1 :]:
            shared = set(a["capabilities"]) & set(b["capabilities"])
            if not shared:
                continue
            key = f"{a['id']}:{b['id']}"
            if key in seen:
                continue
            seen.add(key)
            edges.append(
                {
                    "source": a["id"],
                    "target": b["id"],
                    "shared_capabilities": sorted(shared)[:8],
                    "weight": len(shared),
                }
            )

    for wf in WORKFLOWS:
        steps = [s for s in wf["steps"] if s in by_id]
        for k in range(len(steps) - 1):
            a_id, b_id = steps[k], steps[k + 1]
            key = f"{a_id}:{b_id}"
            rev = f"{b_id}:{a_id}"
            if key in seen or rev in seen:
                continue
            seen.add(key)
            edges.append(
                {
                    "source": a_id,
                    "target": b_id,
                    "shared_capabilities": [],
                    "weight": 1,
                    "workflow": wf["name"],
                }
            )

    # Cap dense graphs for browser force layout
    if len(edges) > 220:
        edges = sorted(edges, key=lambda e: (-int(e.get("weight") or 0), e["source"]))[:220]

    return {"nodes": nodes, "edges": edges, "workflows": WORKFLOWS}


def publish_dispatch(agent_id: str, task: str, **extra: Any) -> None:
    BUS.publish(
        {
            "type": "dispatch",
            "agent_id": agent_id,
            "task": task,
            "ts": time.strftime("%H:%M:%S"),
            **extra,
        }
    )


def publish_complete(agent_id: str, **extra: Any) -> None:
    BUS.publish(
        {
            "type": "complete",
            "agent_id": agent_id,
            "ts": time.strftime("%H:%M:%S"),
            **extra,
        }
    )


def set_simulation(enabled: bool) -> bool:
    global _simulation_enabled
    _simulation_enabled = bool(enabled)
    return _simulation_enabled


def simulation_enabled() -> bool:
    return _simulation_enabled


def ensure_simulation(agents: Optional[List[Dict[str, Any]]] = None) -> None:
    """Start background simulated activity once (opt-in via set_simulation / env).

    The sim loop ALWAYS dispatches HIVE_CORE_AGENTS ids only — never the catalog,
    regardless of what list callers pass.
    """
    global _sim_started
    with _sim_lock:
        if _sim_started:
            return
        _sim_started = True
        _ = agents  # ignored — hive-core only
        ids = [str(a.get("id")) for a in HIVE_CORE_AGENTS if a.get("id")]
        if not ids:
            return

        def _loop() -> None:
            while True:
                if not _simulation_enabled:
                    time.sleep(2)
                    continue
                time.sleep(random.uniform(2.0, 5.0))
                aid = random.choice(ids)
                task = random.choice(_TASK_DESCRIPTIONS)
                publish_dispatch(aid, task, source="simulation")

                def _done(agent: str = aid) -> None:
                    time.sleep(random.uniform(0.8, 3.0))
                    publish_complete(agent, source="simulation")

                threading.Thread(target=_done, daemon=True).start()

        threading.Thread(target=_loop, daemon=True).start()


HIVE_PIPELINE_ROLES = (
    "overseer",
    "router",
    "architect",
    "coder",
    "analyst",
    "governor",
    "memory",
)
MULTI_PIPELINE_ROLES = (
    "researcher",
    "coder",
    "creative",
    "executor",
    "critic",
)
_ORCH_IDS = {
    "ai-orchestrator",
    "hive-mind-coordinator",
    "agents-orchestrator",
    "hive-orchestrator",
}


def _pulse_dispatch(roles: tuple, task: str, source: str, hold: float = 0.35) -> None:
    """Stagger dispatches so Agents UI SSE can paint each node as active."""
    snippet = (task or "")[:80]
    for role in roles:
        publish_dispatch(role, f"{role}: {snippet}", source=source)
        time.sleep(hold)


def _pulse_complete(roles: tuple, source: str, hold: float = 0.25, **extra: Any) -> None:
    for role in roles:
        publish_complete(role, source=source, **extra)
        time.sleep(hold)


def run_agent_task(
    agent_id: str,
    task: str,
    *,
    use_multi: bool = False,
    dry_run: bool = False,
    pulse_only: bool = False,
) -> Dict[str, Any]:
    """Dispatch a Hive agent / multi-agent run and emit activity events.

    Lights the Hive Pipeline graph (staggered) so Agents UI shows live work.
    Multi runs also pulse the multi pipeline.

    ``dry_run`` / ``pulse_only``: publish UI events only — do not call Vulkan.
    """
    agent_id = str(agent_id or "coder").strip() or "coder"
    task = str(task or "").strip()
    want_multi = bool(use_multi) or agent_id in _ORCH_IDS
    hive_core_ids = {
        str(a.get("id"))
        for a in HIVE_CORE_AGENTS
        if "core" in (a.get("tags") or [])
    }
    # Pulse hive cast for multi/orchestrator/core roles — not for every agency agent.
    want_hive_vis = want_multi or agent_id in hive_core_ids or agent_id in _ORCH_IDS
    skip_llm = bool(dry_run) or bool(pulse_only)

    publish_dispatch(agent_id, task, source="hive")
    publish_dispatch("hive-orchestrator", (task or "hive-run")[:120], source="hive")
    try:
        if want_hive_vis:
            _pulse_dispatch(HIVE_PIPELINE_ROLES, task, "hive", hold=0.25 if skip_llm else 0.4)
        if want_multi:
            _pulse_dispatch(MULTI_PIPELINE_ROLES, task, "multi", hold=0.2 if skip_llm else 0.3)

        if skip_llm:
            result = {
                "ok": True,
                "dry_run": True,
                "mode": "pulse_only",
                "note": "No Vulkan call — Agents UI pulse only",
            }
        else:
            from realai.v3_runtime_bridge import run_multi_agent

            prompt = task if want_multi else f"[agent:{agent_id}] {task}"
            result = run_multi_agent(prompt, mode="pipeline")

        if want_multi:
            _pulse_complete(MULTI_PIPELINE_ROLES, "multi", hold=0.15 if skip_llm else 0.25, ok=True)
        if want_hive_vis:
            _pulse_complete(HIVE_PIPELINE_ROLES, "hive", hold=0.15 if skip_llm else 0.25, ok=True)
        publish_complete("hive-orchestrator", source="hive", ok=True)
        publish_complete(agent_id, source="hive", ok=True)
        return {
            "ok": True,
            "agent_id": agent_id,
            "mode": "multi" if want_multi else ("pulse_only" if skip_llm else "pipeline"),
            "hive_vis": want_hive_vis,
            "dry_run": skip_llm,
            "result": result,
        }
    except Exception as exc:
        if want_multi:
            _pulse_complete(MULTI_PIPELINE_ROLES, "multi", hold=0.1, ok=False, error=str(exc))
        if want_hive_vis:
            _pulse_complete(HIVE_PIPELINE_ROLES, "hive", hold=0.1, ok=False, error=str(exc))
        publish_complete("hive-orchestrator", source="hive", ok=False, error=str(exc))
        publish_complete(agent_id, source="hive", ok=False, error=str(exc))
        return {"ok": False, "agent_id": agent_id, "error": str(exc)}
