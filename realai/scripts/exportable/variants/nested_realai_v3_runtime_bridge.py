#!/usr/bin/env python3
"""
v3 Runtime Bridge — wire recovered gold into the live orchestrator safely.

- agent_tools gold: list/search agents, profiles, module inventory (read-only)
- multi-agent gold: planner → worker → critic via Vulkan (optional)
- no write tools, no network tools, no unattended promote apply

Does not require `pip install agent_tools`; loads JSON from known paths.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

_PKG = Path(__file__).resolve().parent
_ROOT = _PKG.parent

AGENTX_AGENTS = Path(
    os.environ.get("REALAI_AGENTS_PATH", str(_ROOT / "agents" / "agentx" / "agents.json"))
)
AGENTX_PROFILES = _ROOT / "agents" / "agentx" / "access_profiles.json"
AGENT_TOOLS_DIRS = [
    _PKG / "agent_tools_gold",
    _ROOT / "realai-core" / "agent_tools",
    _ROOT / "recovered" / "from_agent_tools" / "agent_tools",
]
ORCH_GOLD = _PKG / "orchestration_gold"
HIER_GOLD = _PKG / "hierarchical_agent_gold"

VULKAN_BASE = os.environ.get("REALAI_VULKAN_BASE", "http://127.0.0.1:8080").rstrip("/")
DEFAULT_MODEL = os.environ.get(
    "REALAI_DEFAULT_MODEL",
    "qwen2.5-coder-7b-instruct-q5_k_m.gguf",
)


def _load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _first_agents_json() -> Path:
    for d in AGENT_TOOLS_DIRS:
        p = d / "data" / "agents.json"
        if p.is_file():
            return p
    return AGENTX_AGENTS


def _first_profiles_json() -> Path:
    for d in AGENT_TOOLS_DIRS:
        p = d / "data" / "access_profiles.json"
        if p.is_file():
            return p
    return AGENTX_PROFILES


def agent_tools_status() -> Dict[str, Any]:
    """Inventory of recovered agent_tools packages on disk."""
    packages = []
    for d in AGENT_TOOLS_DIRS:
        if not d.is_dir():
            continue
        py = sorted(p.name for p in d.glob("*.py"))
        subs = {
            "engine": (d / "engine").is_dir(),
            "providers": (d / "providers").is_dir(),
            "tooling": (d / "tooling").is_dir(),
            "data": (d / "data").is_dir(),
        }
        # classify completeness of core modules
        core = ["cli.py", "dashboard.py", "executor.py", "importer.py", "models.py", "registry.py", "runtime.py"]
        core_present = [c for c in core if (d / c).is_file() and (d / c).stat().st_size > 200]
        packages.append({
            "path": str(d),
            "py_top": py,
            "core_modules_ready": core_present,
            "core_ready_count": len(core_present),
            "subpackages": subs,
            "agents_data": (d / "data" / "agents.json").is_file(),
        })
    agents = _load_json(_first_agents_json()) or []
    profiles = _load_json(_first_profiles_json()) or []
    return {
        "service": "agent_tools_bridge",
        "mode": "read_only",
        "packages": packages,
        "agents_count": len(agents) if isinstance(agents, list) else 0,
        "profiles_count": len(profiles) if isinstance(profiles, list) else 0,
        "agents_path": str(_first_agents_json()),
        "profiles_path": str(_first_profiles_json()),
        "orchestration_gold": ORCH_GOLD.is_dir(),
        "hierarchical_agent_gold": HIER_GOLD.is_dir(),
        "note": "Write/network tooling not exposed. engine/providers/tooling may be placeholders.",
    }


def list_agent_tools_agents(limit: int = 50, query: str = "") -> Dict[str, Any]:
    raw = _load_json(_first_agents_json()) or []
    if not isinstance(raw, list):
        return {"count": 0, "agents": [], "error": "agents_json_not_list"}
    q = (query or "").lower().strip()
    out = []
    for a in raw:
        if not isinstance(a, dict):
            continue
        if q:
            hay = " ".join([
                str(a.get("id") or ""),
                str(a.get("role") or ""),
                str(a.get("description") or ""),
                " ".join(a.get("tags") or []),
                " ".join(a.get("capabilities") or []),
            ]).lower()
            if q not in hay:
                continue
        out.append({
            "id": a.get("id"),
            "role": a.get("role"),
            "risk_level": a.get("risk_level"),
            "capabilities": (a.get("capabilities") or [])[:12],
            "tags": (a.get("tags") or [])[:8],
            "preferred_profile": a.get("preferred_profile"),
        })
        if len(out) >= limit:
            break
    return {
        "count": len(out),
        "total_in_file": len(raw),
        "query": query or None,
        "source": str(_first_agents_json()),
        "agents": out,
    }


def list_access_profiles() -> Dict[str, Any]:
    raw = _load_json(_first_profiles_json()) or []
    if not isinstance(raw, list):
        return {"count": 0, "profiles": [], "error": "profiles_not_list"}
    profiles = []
    for p in raw:
        if not isinstance(p, dict):
            continue
        profiles.append({
            "name": p.get("name"),
            "write": bool(p.get("write", False)),
            "network": bool(p.get("network", False)),
            "secrets": p.get("secrets", "none"),
            "tools": p.get("tools") or [],
            "notes": p.get("notes") or "",
        })
    return {
        "count": len(profiles),
        "source": str(_first_profiles_json()),
        "profiles": profiles,
        "note": "Profiles are informational; orchestrator does not grant write/network from these yet.",
    }


def assess_agent_profile(agent_id: str, profile_name: str = "balanced") -> Dict[str, Any]:
    agents = _load_json(_first_agents_json()) or []
    profiles = _load_json(_first_profiles_json()) or []
    agent = next((a for a in agents if isinstance(a, dict) and a.get("id") == agent_id), None)
    if not agent:
        return {"error": "agent_not_found", "agent_id": agent_id}
    profile = next((p for p in profiles if isinstance(p, dict) and p.get("name") == profile_name), None)
    if not profile:
        return {"error": "profile_not_found", "profile": profile_name}
    required = set(agent.get("required_tools") or [])
    granted = set(profile.get("tools") or [])
    missing = sorted(required - granted)
    return {
        "agent": agent_id,
        "profile": profile_name,
        "pass": len(missing) == 0,
        "missing_tools": missing,
        "extra_tools": sorted(granted - required),
        "risk_level": agent.get("risk_level"),
        "write_allowed_by_profile": bool(profile.get("write")),
        "network_allowed_by_profile": bool(profile.get("network")),
        "enforcement": "informational_only",
    }


class _VulkanChatClient:
    """Minimal OpenAI-compatible chat client against local Vulkan llama-server."""

    def __init__(self, base: str = VULKAN_BASE, model: str = DEFAULT_MODEL, timeout: float = 180.0):
        self.base = base.rstrip("/")
        self.model = model
        self.timeout = timeout
        # surface matching RealAIClient-ish nesting
        self.chat = self

    @property
    def completions(self) -> "_VulkanChatClient":
        return self

    def create(
        self,
        *,
        model: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.4,
        max_tokens: int = 512,
        **kwargs: Any,
    ) -> Any:
        payload = {
            "model": model or self.model,
            "messages": messages or [],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base}/v1/chat/completions",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        class _Msg:
            def __init__(self, content: str):
                self.content = content

        class _Choice:
            def __init__(self, content: str):
                self.message = _Msg(content)

        class _Resp:
            def __init__(self, content: str, raw: dict):
                self.choices = [_Choice(content)]
                self.raw = raw

        content = ""
        try:
            content = body["choices"][0]["message"]["content"]
        except Exception:
            content = json.dumps(body)[:2000]
        return _Resp(content, body)


def run_multi_agent(
    task: str,
    *,
    mode: str = "pipeline",
    max_tokens: int = 384,
    temperature: float = 0.3,
) -> Dict[str, Any]:
    """
    Run planner → worker → critic using orchestration_gold + Vulkan.

    Falls back to a simple sequential prompt chain if gold package import fails.
    """
    task = (task or "").strip()
    if not task:
        return {"ok": False, "error": "empty_task"}

    client = _VulkanChatClient()

    # Prefer recovered orchestration_gold package
    try:
        import importlib.util
        import sys

        # Ensure package import path
        if str(_PKG) not in sys.path:
            sys.path.insert(0, str(_PKG))
        # Load as namespace package orchestration_gold
        from realai.orchestration_gold.agent import BaseAgent
        from realai.orchestration_gold.orchestrator import Orchestrator

        orch = Orchestrator(client)
        orch.add_agent(BaseAgent(
            name="planner",
            role=(
                "You are the Planner agent for RealAI. Break the user task into "
                "clear steps. Output a short plan only."
            ),
            realai_client=client,
            temperature=temperature,
            max_tokens=max_tokens,
        ))
        orch.add_agent(BaseAgent(
            name="worker",
            role=(
                "You are the Worker agent for RealAI. Execute the plan. "
                "Be concrete and produce the main deliverable."
            ),
            realai_client=client,
            temperature=temperature,
            max_tokens=max_tokens,
        ))
        orch.add_agent(BaseAgent(
            name="critic",
            role=(
                "You are the Critic agent for RealAI. Review the worker output. "
                "Note gaps, risks, and a final improved answer if needed."
            ),
            realai_client=client,
            temperature=min(temperature, 0.4),
            max_tokens=max_tokens,
        ))
        if mode == "parallel":
            # split task into pseudo subtasks
            results = orch.run_parallel([
                f"Plan approach for: {task}",
                f"Execute primary work for: {task}",
                f"Critique likely risks for: {task}",
            ], agents=["planner", "worker", "critic"])
            return {
                "ok": True,
                "mode": "parallel",
                "engine": "orchestration_gold",
                "results": results,
                "final_output": (results[-1] or {}).get("output") if results else "",
            }
        result = orch.run_pipeline(task, agents=["planner", "worker", "critic"])
        # Prefer last non-empty substantive step as final (skip ack-only lines)
        final = (result.get("final_output") or "").strip()
        if len(final) < 40 or final.lower().startswith("understood"):
            for step in reversed(result.get("steps") or []):
                out = str((step or {}).get("output") or "").strip()
                if out and len(out) >= 20 and not out.lower().startswith("understood"):
                    final = out
                    break
        result["final_output"] = final
        result["ok"] = bool(result.get("success"))
        result["mode"] = "pipeline"
        result["engine"] = "orchestration_gold"
        return result
    except Exception as e:
        # Fallback sequential without package
        steps = []
        context = ""
        roles = [
            ("planner", "Break the task into a short plan only."),
            ("worker", "Execute the plan and produce the deliverable."),
            ("critic", "Review and produce the final improved answer."),
        ]
        current = task
        for name, role in roles:
            messages = [
                {"role": "system", "content": f"You are RealAI multi-agent role: {name}. {role}"},
                {"role": "user", "content": f"Task: {current}\n\nPrior context:\n{context[:3000]}"},
            ]
            try:
                resp = client.chat.completions.create(
                    messages=messages, temperature=temperature, max_tokens=max_tokens
                )
                out = resp.choices[0].message.content
                steps.append({"agent": name, "output": out, "success": True, "error": None})
                context += f"\n\n[{name}]\n{out}"
                current = out
            except Exception as ex:
                steps.append({"agent": name, "output": "", "success": False, "error": str(ex)})
                return {
                    "ok": False,
                    "mode": mode,
                    "engine": "fallback_sequential",
                    "import_error": str(e),
                    "steps": steps,
                    "final_output": "",
                }
        return {
            "ok": True,
            "mode": "pipeline",
            "engine": "fallback_sequential",
            "import_error": str(e),
            "steps": steps,
            "final_output": steps[-1]["output"] if steps else "",
            "success": all(s["success"] for s in steps),
        }


def tools_catalog() -> List[Dict[str, Any]]:
    """OpenAI tools-format catalog for orchestrator."""
    return [
        {
            "type": "function",
            "function": {
                "name": "self_heal_status",
                "description": "Multi-repo self-heal artifact + ability coverage status",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "self_heal_assemble",
                "description": "Rebuild gold index + promote queue from scans (requires REALAI_SELF_IMPROVE)",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_agents",
                "description": "List RealAI agentx agents (live hive)",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "training_status",
                "description": "Training data availability",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "agent_tools_status",
                "description": "Status of recovered agent_tools gold packages (read-only)",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "agent_tools_list_agents",
                "description": "Search/list agents from agent_tools registry data (read-only)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "agent_tools_list_profiles",
                "description": "List access profiles (informational, no write grant)",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "agent_tools_assess",
                "description": "Assess whether a profile covers an agent's required tools (read-only)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string"},
                        "profile": {"type": "string"},
                    },
                    "required": ["agent_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "multi_agent_run",
                "description": "Run planner→worker→critic multi-agent pipeline via local Vulkan (expensive)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "mode": {"type": "string", "enum": ["pipeline", "parallel"]},
                    },
                    "required": ["task"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "ability_coverage",
                "description": "Technical-rundown ability coverage percentage",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ]
