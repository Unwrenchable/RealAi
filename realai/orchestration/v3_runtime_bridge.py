#!/usr/bin/env python3
"""
RealAI v3 runtime bridge — lives entirely inside RealAI-clean.

Connects orchestrator chat to:
  - full tools catalog (native + safe registry tools)
  - core.tools registry (code_exec, web_search, file, web3)
  - multi-agent planner→…→synthesizer pipeline (Vulkan-backed when available)
  - agentx roster from agents/agentx/agents.json
  - living agent_tools package (promoted gold) + agentx roster

This is product code for C:\\RealAI-clean — not a shim to C:\\realai.
"""
from __future__ import annotations

import json
import re
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

_PKG = Path(__file__).resolve().parent
_REALAI_PKG = _PKG.parent  # .../realai
_ROOT = _REALAI_PKG  # back-compat alias (package dir)
_PRODUCT_ROOT = _REALAI_PKG.parent  # .../RealAI-clean (top-level agent_tools/abilities)
_HIVE_ARCHETYPES = (
    "overseer",
    "coder",
    "architect",
    "analyst",
    "memory",
    "governor",
    "router",
)

# Prefer product root so top-level agent_tools wins over realai/agent_tools shadow
for _p in (str(_PRODUCT_ROOT), str(_REALAI_PKG)):
    if _p in sys.path:
        sys.path.remove(_p)
sys.path[0:0] = [str(_PRODUCT_ROOT), str(_REALAI_PKG)]


def _product_root() -> Path:
    """Canonical product/workspace root (C:\\RealAI-clean) — never nested realai/."""
    try:
        from realai.workspace import apply_workspace, product_root, realai_workspace

        apply_workspace()
        ws = realai_workspace()
        return ws if ws.is_dir() else product_root()
    except Exception:
        return _PRODUCT_ROOT


def _agents_path() -> Path:
    env = (os.environ.get("REALAI_AGENTS_PATH") or "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if p.is_dir():
            cand = p / "agents.json"
            if cand.is_file():
                return cand
        return p
    return _product_root() / "agents" / "agentx" / "agents.json"


def _github_agents_dir() -> Path:
    return _product_root() / ".github" / "agents"


# Back-compat aliases — always product-root (never nested realai/agents twin).
_AGENTS = _agents_path()
_GITHUB_AGENTS = _github_agents_dir()

VULKAN_BASE = os.environ.get("REALAI_VULKAN_BASE", "http://127.0.0.1:8080").rstrip("/")
ORCH_BASE = os.environ.get("REALAI_API_BASE", "http://127.0.0.1:8001").rstrip("/")
DEFAULT_MODEL = os.environ.get("REALAI_DEFAULT_MODEL", "realai-default-coder")
BACKEND_MODEL = os.environ.get(
    "REALAI_BACKEND_MODEL", "qwen2.5-coder-7b-instruct-q5_k_m.gguf"
)

_CORE_TOOLS = None  # lazy ToolRegistry singleton


def _fn(
    name: str,
    description: str,
    properties: Optional[Dict] = None,
    required: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties or {},
                "required": required or [],
            },
        },
    }


def _core_tool_registry():
    """Lazy singleton: core.tools registry with built-ins registered."""
    global _CORE_TOOLS
    if _CORE_TOOLS is not None:
        return _CORE_TOOLS if _CORE_TOOLS is not False else None
    # Ensure realai/ is on path so top-level ``core`` resolves
    realai_s = str(_REALAI_PKG)
    if realai_s not in sys.path:
        sys.path.append(realai_s)
    try:
        from core.tools.registry import ToolRegistry
        from core.tools.code import CodeExecutionTool
        from core.tools.file import FileTool
        from core.tools.web import WebSearchTool

        reg = ToolRegistry()
        reg.register(WebSearchTool())
        reg.register(CodeExecutionTool())
        # Scope file I/O to product root (not .hive cwd)
        reg.register(FileTool(str(_product_root())))
        try:
            from core.tools.web3 import Web3Tool

            reg.register(Web3Tool())
        except Exception:
            pass
        _CORE_TOOLS = reg
        return _CORE_TOOLS
    except Exception:
        _CORE_TOOLS = False
        return None


def _core_tools_openai() -> List[Dict[str, Any]]:
    """Map registered core tools into OpenAI tool schema (namespaced core.*)."""
    reg = _core_tool_registry()
    if not reg:
        return []
    out: List[Dict[str, Any]] = []
    for tool in reg.list():
        name = getattr(tool, "name", None) or ""
        if not name:
            continue
        schema = getattr(tool, "params_schema", None) or {}
        if isinstance(schema, dict) and schema and "type" not in schema:
            props = schema
            required = list(props.keys())[:1]
            parameters: Dict[str, Any] = {
                "type": "object",
                "properties": props,
                "required": required,
            }
        elif isinstance(schema, dict) and schema:
            parameters = schema
        else:
            parameters = {"type": "object", "properties": {}}
        out.append(
            {
                "type": "function",
                "function": {
                    "name": f"core.{name}",
                    "description": (getattr(tool, "description", None) or name)
                    + " [core.tools]",
                    "parameters": parameters,
                },
            }
        )
    return out


def tools_catalog() -> List[Dict[str, Any]]:
    """OpenAI-style tools the orchestrator advertises to clients / craft."""
    tools: List[Dict[str, Any]] = [
        _fn("self_heal_status", "Self-heal artifact status and ability flags"),
        _fn("self_heal_assemble", "Assemble gold index / promote queue (self-heal)"),
        _fn(
            "self_heal_promote_dry",
            "Preview curated promote (dry-run, no writes)",
        ),
        _fn("list_agents", "List RealAI agentx agents (roles, risk, tags)"),
        _fn(
            "agent_info",
            "Get one agent by id",
            {"agent_id": {"type": "string"}},
            ["agent_id"],
        ),
        _fn("recovery_status", "Recovery inventory (LoRA, staged modules)"),
        _fn(
            "list_lora_adapters",
            "List recovered PEFT LoRA adapters",
            {"limit": {"type": "integer"}},
        ),
        _fn("local_llama_health", "Health-check Vulkan/llama-server backend"),
        _fn(
            "voice_health",
            "Probe RealAI Voice provider + Vulkan/hive/TTS HTTP backends",
        ),
        _fn(
            "voice_inventory",
            "List local TTS weights under C:\\models\\checkpoints_lora",
        ),
        _fn(
            "voice_speak",
            "Speak text via local RealAI TTS (Kokoro/Fish/XTTS/Windows SAPI)",
            {
                "text": {"type": "string"},
                "voice": {"type": "string"},
                "backend": {"type": "string"},
            },
            ["text"],
        ),
        _fn(
            "voice_listen",
            "Transcribe base64 audio with local Whisper when available",
            {"audio_b64": {"type": "string"}},
            ["audio_b64"],
        ),
        _fn("training_status", "Training data / pipeline status"),
        _fn("ability_coverage", "Ability catalog coverage summary"),
        _fn(
            "multi_agent_run",
            "Run multi-agent pipeline (planner/researcher/critic/executor/synthesizer)",
            {
                "task": {"type": "string"},
                "mode": {"type": "string", "description": "pipeline or parallel"},
            },
            ["task"],
        ),
        _fn(
            "craft_run",
            "Run a Craft toolkit action (doctor, heal, multi, list, agents, catalog, …)",
            {
                "action": {"type": "string"},
                "goal": {"type": "string"},
                "input": {"type": "string"},
                "task": {"type": "string"},
                "path": {"type": "string"},
                "prompt": {"type": "string"},
            },
            ["action"],
        ),
        _fn(
            "craft_chat",
            "One-shot Craft chat (tools + reply) without opening the REPL",
            {"prompt": {"type": "string"}, "input": {"type": "string"}},
            ["prompt"],
        ),
        _fn(
            "hive_status",
            "Hive agents + organs + ability coverage snapshot",
            {"action": {"type": "string"}},
        ),
        _fn(
            "hive_run",
            "Run hive cycle, multi-agent, or ability via operator surface",
            {
                "action": {"type": "string", "description": "cycle|multi|ability"},
                "task": {"type": "string"},
                "ability": {"type": "string"},
                "agent": {"type": "string"},
            },
        ),
        _fn(
            "orchestration_surface",
            "List/run unified realai/orchestration modules (v3, bridge, hive_router, sdk, nests, tts)",
            {
                "action": {"type": "string", "description": "list|run|cycle"},
                "orch": {"type": "string"},
                "input": {"type": "string"},
                "nest": {"type": "string"},
            },
        ),
        _fn(
            "plugins_surface",
            "Inventory/unify realai/plugins (live vs salvage vs junk) + quarantine organize",
            {
                "action": {
                    "type": "string",
                    "description": "list|run|quarantine_plan|quarantine",
                },
                "plugin": {"type": "string"},
                "dry_run": {"type": "boolean"},
                "apply_salvage": {"type": "boolean"},
                "input": {"type": "string"},
            },
        ),
        _fn(
            "learn_git",
            "Scan a git source (path / owner/repo / URL); write packet; optional plugin stub. No heal.",
            {
                "source": {"type": "string", "description": "local path, owner/repo, or HTTPS URL"},
                "write": {"type": "boolean", "description": "scaffold plugins/<slug>_coach"},
                "refresh": {"type": "boolean"},
                "input": {"type": "string"},
            },
        ),
        _fn(
            "agents_surface",
            "List/run hive + pipeline agents (overseer/coder/multi/self_heal/agentx)",
            {
                "action": {"type": "string", "description": "list|run|cycle"},
                "agent": {"type": "string"},
                "task": {"type": "string"},
                "input": {"type": "string"},
            },
        ),
        _fn(
            "agent_tools_surface",
            "List/run agent_tools package (filesystem/http/solana/memory/profiles)",
            {
                "action": {"type": "string", "description": "list|run"},
                "tool": {"type": "string"},
                "dry_run": {"type": "boolean"},
                "input": {"type": "string"},
            },
        ),
        _fn(
            "core_surface",
            "List/run realai/core subsystems (agents/tools/security/voice/web3/identity/…)",
            {
                "action": {"type": "string", "description": "list|run"},
                "core": {"type": "string"},
                "input": {"type": "string"},
            },
        ),
        _fn(
            "modules_surface",
            "List/run living modules/ packages (organs, agents_advanced, desktop_unique, …)",
            {
                "action": {"type": "string", "description": "list|run"},
                "module": {"type": "string"},
                "input": {"type": "string"},
            },
        ),
        _fn(
            "repo_surface",
            "Repo authority map — where packages live (root vs realai/)",
            {
                "action": {"type": "string", "description": "list|where"},
                "name": {"type": "string"},
            },
        ),
        _fn(
            "organs_task",
            "Run synthetic organs hive on a goal",
            {"goal": {"type": "string"}},
            ["goal"],
        ),
        _fn(
            "omnibrain",
            "Atomic Fizz omnibrain encounter decision (heuristic or Hive LLM)",
            {
                "region": {"type": "string"},
                "action": {"type": "string", "description": "decide|fallback|prompt"},
                "ar_mode": {"type": "boolean"},
                "player": {"type": "object"},
                "cell": {"type": "object"},
                "worldstate": {"type": "object"},
                "llm": {"type": "boolean"},
            },
        ),
        _fn(
            "world_brain",
            "Atomic Fizz world-brain prompt/context/region influence builders",
            {
                "action": {"type": "string", "description": "prompt|context|region"},
                "region": {"type": "string"},
                "seed": {"type": "object"},
            },
        ),
        _fn(
            "overseer",
            "OVERSEER-77 wasteland persona chat (Atomic Fizz lore prompt)",
            {
                "text": {"type": "string"},
                "action": {"type": "string", "description": "chat|prompt"},
                "lore_context": {"type": "string"},
            },
        ),
        _fn(
            "rackup_invoke",
            "Invoke RackUp coach ability (rating, SOTD, pyramid, etc.)",
            {
                "ability": {"type": "string"},
                "player": {
                    "type": "object",
                    "description": "Player profile (display_name, discipline, rating). Maps to ctx.player.",
                },
                "payload": {
                    "type": "object",
                    "description": "Ability input (question, won, outcome, scores, opponent). Maps to ctx.payload.",
                },
                "player_id": {"type": "string"},
            },
            ["ability"],
        ),
        _fn(
            "aura_memory",
            "Remember or recall via Aura memory",
            {
                "action": {"type": "string", "description": "remember|recall"},
                "text": {"type": "string"},
                "query": {"type": "string"},
                "top_k": {"type": "integer"},
            },
        ),
        _fn("device_selector", "Preferred compute device (cuda/directml/cpu)"),
        _fn(
            "self_extend",
            "Self-extend: propose capability growth steps",
            {"goal": {"type": "string"}},
        ),
        _fn(
            "self_repair",
            "Self-repair: diagnose and fix stack/config issues",
            {"issue": {"type": "string"}},
        ),
        _fn(
            "system_scan",
            "Scan workspace or install for structure/issues",
            {"path": {"type": "string"}},
        ),
        _fn(
            "workspace_list",
            "List files under REALAI_WORKSPACE (or path)",
            {"path": {"type": "string"}},
        ),
        _fn(
            "workspace_read",
            "Read a file under REALAI_WORKSPACE",
            {
                "path": {"type": "string"},
                "start": {"type": "integer"},
                "limit": {"type": "integer"},
            },
            ["path"],
        ),
        _fn(
            "workspace_grep",
            "Search files under REALAI_WORKSPACE",
            {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
                "glob": {"type": "string"},
            },
            ["pattern"],
        ),
        _fn(
            "execute_code",
            "Run short Python in a restricted sandbox",
            {
                "code": {"type": "string"},
                "language": {"type": "string"},
            },
            ["code"],
        ),
        _fn(
            "web_research",
            "Lightweight web research (stdlib; best-effort)",
            {
                "query": {"type": "string"},
                "max_results": {"type": "integer"},
            },
            ["query"],
        ),
        _fn(
            "read_file",
            "Read a UTF-8 file in the workspace (line numbers)",
            {
                "target_file": {"type": "string"},
                "offset": {"type": "integer"},
                "limit": {"type": "integer"},
            },
            ["target_file"],
        ),
        _fn(
            "list_dir",
            "List files under a workspace path",
            {"target_directory": {"type": "string"}},
        ),
        _fn(
            "search_replace",
            "Replace text in a workspace file",
            {
                "file_path": {"type": "string"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"},
                "replace_all": {"type": "boolean"},
            },
            ["file_path", "old_string", "new_string"],
        ),
        _fn(
            "run_terminal_command",
            "Run a shell command in the workspace root",
            {
                "command": {"type": "string"},
                "description": {"type": "string"},
                "timeout": {"type": "integer"},
            },
            ["command"],
        ),
        _fn(
            "agent_tools_status",
            "Status of living agent_tools (gold) package + agentx",
        ),
        _fn(
            "agent_tools_list_agents",
            "List agents from agent_tools gold + agentx roster",
            {"limit": {"type": "integer"}, "query": {"type": "string"}},
        ),
        _fn(
            "agent_tools_list_profiles",
            "List access profiles (safe/balanced/power + bridge)",
        ),
        _fn(
            "agent_tools_assess",
            "Assess agent id against a profile (gold assess when available)",
            {
                "agent_id": {"type": "string"},
                "profile": {"type": "string"},
            },
            ["agent_id"],
        ),
        _fn(
            "agent_tools_list_tools",
            "List wired agent_tools tooling registry (http/filesystem/crypto/solana)",
        ),
        _fn(
            "agent_tools_invoke",
            "Invoke a gold tooling tool under a profile (dry_run default true)",
            {
                "tool": {
                    "type": "string",
                    "description": "filesystem|http|crypto|solana",
                },
                "payload": {"type": "object"},
                "profile": {
                    "type": "string",
                    "description": "safe|balanced|power",
                },
                "dry_run": {"type": "boolean"},
                "allowed_tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Override allowed tool names; default from profile",
                },
            },
            ["tool"],
        ),
    ]

    # Soft-merge ability.* entries that are LIVE/PARTIAL for discovery
    try:
        from realai.tools import TOOL_REGISTRY

        TOOL_REGISTRY.ensure_ability_catalog_loaded()
        for t in TOOL_REGISTRY.to_openai_format(include_catalog=True):
            fn = t.get("function") or {}
            name = fn.get("name") or ""
            if not name.startswith("ability."):
                continue
            desc = (fn.get("description") or "").upper()
            if any(s in desc for s in ("LIVE", "PARTIAL", "CODE")):
                if not any((x.get("function") or {}).get("name") == name for x in tools):
                    tools.append(t)
    except Exception:
        pass

    # Core product tools (core.tools registry)
    try:
        for t in _core_tools_openai():
            name = (t.get("function") or {}).get("name")
            if name and not any((x.get("function") or {}).get("name") == name for x in tools):
                tools.append(t)
    except Exception:
        pass

    return tools


def _load_agents() -> List[Dict[str, Any]]:
    agents_file = _agents_path()
    if not agents_file.is_file():
        return []
    try:
        data = json.loads(agents_file.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return list(data.get("agents") or [])
    return []


def _load_github_hive_agents() -> List[Dict[str, Any]]:
    """Load hive agent manifests from .github/agents/*.json (nextgen hive)."""
    github_agents = _github_agents_dir()
    root = _product_root()
    if not github_agents.is_dir():
        return []
    out: List[Dict[str, Any]] = []
    for path in sorted(github_agents.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if not isinstance(data, dict) or not data.get("id"):
            continue
        agent = dict(data)
        agent["_source"] = "github_agents"
        try:
            agent["_path"] = str(path.relative_to(root)).replace("\\", "/")
        except ValueError:
            agent["_path"] = str(path)
        if agent.get("hive") is None:
            # Treat archetype filenames / tags as hive even without explicit flag
            aid = str(agent.get("id") or "").lower()
            tags = [str(t).lower() for t in (agent.get("tags") or [])]
            agent["hive"] = aid in _HIVE_ARCHETYPES or "hive" in tags
        out.append(agent)
    return out


def route_model(agent_role: str = "", task_description: str = "") -> str:
    """Map hive agent role / task text to a model id (nextgen_hive routing table)."""
    role = (agent_role or "").strip().lower()
    task = (task_description or "").strip().lower()
    table = {
        "coder": "realai-default-coder-10",
        "architect": "qwen3-27b",
        "overseer": "realai-1.0-instruct",
        "orchestrator": "realai-1.0-instruct",
        "analyst": "local-llama-1b",
        "memory": "realai-embeddings",
        "governor": "local-llama-1b",
        "router": "local-llama-1b",
    }
    if role in table:
        return table[role]
    if any(k in task for k in ("code", "debug", "refactor", "implement", "patch")):
        return table["coder"]
    if any(k in task for k in ("architect", "design", "structure", "multi-module")):
        return table["architect"]
    if any(k in task for k in ("embed", "memory", "similarity", "recall")):
        return table["memory"]
    if any(k in task for k in ("summar", "explain", "analy")):
        return table["analyst"]
    return "local-llama-1b"


def hive_agents_status() -> Dict[str, Any]:
    """Validate the seven nextgen hive archetypes under .github/agents."""
    loaded = {str(a.get("id")): a for a in _load_github_hive_agents() if a.get("id")}
    present = [aid for aid in _HIVE_ARCHETYPES if aid in loaded]
    missing = [aid for aid in _HIVE_ARCHETYPES if aid not in loaded]
    return {
        "ok": len(missing) == 0,
        "hive_mode": len(missing) == 0,
        "required": list(_HIVE_ARCHETYPES),
        "present": present,
        "missing": missing,
        "count": len(loaded),
        "path": str(_github_agents_dir()),
        "routing_sample": {r: route_model(r) for r in _HIVE_ARCHETYPES},
        "agents": [
            {
                "id": loaded[aid].get("id"),
                "role": loaded[aid].get("role"),
                "preferred_model": loaded[aid].get("preferred_model")
                or route_model(aid),
            }
            for aid in present
        ],
    }


def _ensure_product_agent_tools() -> None:
    """Force repo-root agent_tools onto sys.path / sys.modules (not realai/ shadow)."""
    root = _product_root()
    root_s = str(root)
    if root_s in sys.path:
        sys.path.remove(root_s)
    sys.path.insert(0, root_s)
    auth = root / "agent_tools" / "__init__.py"
    cur = sys.modules.get("agent_tools")
    cur_file = Path(getattr(cur, "__file__", "") or "")
    try:
        cur_ok = cur is not None and cur_file.resolve() == auth.resolve()
    except Exception:
        cur_ok = False
    if cur_ok:
        return
    # Drop shadow / partial imports so tooling + agents_impl resolve under product root
    for key in list(sys.modules):
        if key == "agent_tools" or key.startswith("agent_tools."):
            del sys.modules[key]
    if auth.is_file():
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "agent_tools",
            auth,
            submodule_search_locations=[str(root / "agent_tools")],
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules["agent_tools"] = mod
            spec.loader.exec_module(mod)


def _agent_tools_pkg():
    """Import living agent_tools package (repo-root)."""
    try:
        _ensure_product_agent_tools()
        import agent_tools  # noqa: F401
        from agent_tools import registry as reg
        from agent_tools.tooling.registry import ToolRegistry

        return reg, ToolRegistry, None
    except Exception as e:
        return None, None, str(e)


def _merge_agent_dicts() -> List[Dict[str, Any]]:
    """Hive (.github/agents) + agentx roster + gold package (first wins by id)."""
    by_id: Dict[str, Dict[str, Any]] = {}
    # Hive agents first so /agents surfaces overseer/coder/... even when ids collide
    for a in _load_github_hive_agents():
        if isinstance(a, dict) and a.get("id"):
            by_id[str(a["id"])] = a
    for a in _load_agents():
        if isinstance(a, dict) and a.get("id"):
            aid = str(a["id"])
            if aid in by_id:
                continue
            by_id[aid] = {**a, "_source": "agentx"}
    reg, _, err = _agent_tools_pkg()
    if reg is not None:
        try:
            for aid, agent in reg.load_agents().items():
                if aid in by_id:
                    continue
                by_id[aid] = {
                    "id": agent.id,
                    "role": agent.role,
                    "description": agent.description,
                    "tags": list(agent.tags),
                    "capabilities": list(agent.capabilities),
                    "required_tools": list(agent.required_tools),
                    "preferred_profile": agent.preferred_profile,
                    "risk_level": agent.risk_level,
                    "_source": "agent_tools",
                }
        except Exception:
            pass
    return list(by_id.values())


def list_agent_tools_agents(limit: int = 50, query: str = "") -> Dict[str, Any]:
    agents = _merge_agent_dicts()
    q = (query or "").lower().strip()
    # Prefer hive archetypes at the front of the roster
    def _sort_key(a: Dict[str, Any]) -> tuple:
        aid = str(a.get("id") or "").lower()
        if aid in _HIVE_ARCHETYPES:
            return (0, _HIVE_ARCHETYPES.index(aid))
        if a.get("hive") or a.get("_source") == "github_agents":
            return (1, aid)
        return (2, aid)

    agents = sorted(agents, key=_sort_key)
    out = []
    for a in agents:
        if not isinstance(a, dict):
            continue
        blob = json.dumps(a, default=str).lower()
        if q and q not in blob:
            continue
        tags = a.get("tags") or []
        aid = str(a.get("id") or "")
        out.append(
            {
                "id": a.get("id"),
                "role": a.get("role"),
                "risk_level": a.get("risk_level"),
                "tags": tags[:8],
                "capabilities": (a.get("capabilities") or [])[:8],
                "preferred_profile": a.get("preferred_profile"),
                "preferred_model": a.get("preferred_model")
                or route_model(aid),
                "hive": bool(a.get("hive")),
                "source": a.get("_source"),
            }
        )
        if len(out) >= max(1, int(limit)):
            break
    reg, _, err = _agent_tools_pkg()
    hive = hive_agents_status()
    return {
        "ok": True,
        "count": len(out),
        "agents": out,
        "agentx_path": str(_agents_path()),
        "github_agents_path": str(_github_agents_dir()),
        "product_root": str(_product_root()),
        "workspace": str(_product_root()),
        "hive": {
            "mode": hive.get("hive_mode"),
            "present": hive.get("present"),
            "missing": hive.get("missing"),
        },
        "gold_package": err is None,
        "gold_error": err,
    }


def agent_tools_status() -> Dict[str, Any]:
    agents = _load_agents()
    tagged = [
        a
        for a in agents
        if isinstance(a, dict)
        and any(
            "agent-tools" in str(t).lower() or "agent_tools" in str(t).lower()
            for t in (a.get("tags") or [])
        )
    ]
    reg, ToolRegistry, err = _agent_tools_pkg()
    gold: Dict[str, Any] = {"ok": False, "error": err}
    if reg is not None:
        try:
            gold = reg.package_status()
        except Exception as e:
            gold = {"ok": False, "error": str(e)}
    gold_path = _ROOT / "agent_tools"
    marker = _PKG / "agent_tools_gold" / "cli.py"
    hive = hive_agents_status()
    return {
        "ok": True,
        "in_tree": True,
        "agents_total": len(agents),
        "agent_tools_tagged": len(tagged),
        "agents_path": str(_agents_path()),
        "github_agents_path": str(_github_agents_dir()),
        "product_root": str(_product_root()),
        "workspace": str(_product_root()),
        "hive": hive,
        "bridge": "realai.v3_runtime_bridge",
        "multi_agent": True,
        "gold": gold,
        "gold_package_path": str(gold_path),
        "gold_marker": marker.is_file(),
        "core_tools": bool(_core_tool_registry()),
        "note": "Hive agents from .github/agents merge first; agentx + agent_tools gold fill the rest.",
    }


def list_access_profiles() -> Dict[str, Any]:
    profiles: List[Dict[str, Any]] = [
        {
            "id": "strict",
            "description": "Low risk only; no code exec; read-mostly tools",
        },
        {
            "id": "balanced",
            "description": "Default: workspace tools + multi-agent + heal",
        },
        {
            "id": "open",
            "description": "Includes restricted tools (sandbox code, promote force)",
        },
    ]
    reg, _, err = _agent_tools_pkg()
    gold_profiles: List[Dict[str, Any]] = []
    if reg is not None:
        try:
            for name, p in reg.load_profiles().items():
                gold_profiles.append(
                    {
                        "id": name,
                        "tools": list(p.tools),
                        "write": p.write,
                        "network": p.network,
                        "secrets": p.secrets,
                        "notes": p.notes,
                        "source": "agent_tools",
                    }
                )
        except Exception as e:
            err = str(e)
    return {
        "ok": True,
        "profiles": profiles,
        "gold_profiles": gold_profiles,
        "gold_error": err,
    }


def assess_agent_profile(agent_id: str, profile: str = "balanced") -> Dict[str, Any]:
    reg, _, _ = _agent_tools_pkg()
    if reg is not None:
        try:
            agents = reg.load_agents()
            profiles = reg.load_profiles()
            pname = (profile or "balanced").lower()
            if pname == "strict":
                pname = "safe"
            if pname == "open":
                pname = "power"
            agent = agents.get(str(agent_id))
            prof = profiles.get(pname) or profiles.get(profile or "")
            if agent and prof:
                result = reg.assess_agent_access(agent, prof)
                result["ok"] = True
                result["source"] = "agent_tools"
                return result
        except Exception:
            pass
    agents = {str(a.get("id")): a for a in _merge_agent_dicts() if isinstance(a, dict)}
    agent = agents.get(str(agent_id))
    if not agent:
        return {"ok": False, "error": f"unknown_agent:{agent_id}"}
    risk = str(agent.get("risk_level") or "medium").lower()
    profile = (profile or "balanced").lower()
    allowed = True
    reasons = []
    if profile == "strict" and risk not in ("low", "none"):
        allowed = False
        reasons.append(f"risk_level={risk} blocked by strict profile")
    if profile == "balanced" and risk in ("critical", "extreme"):
        allowed = False
        reasons.append(f"risk_level={risk} blocked by balanced profile")
    tools_needed = agent.get("required_tools") or []
    return {
        "ok": True,
        "agent_id": agent_id,
        "profile": profile,
        "allowed": allowed,
        "risk_level": risk,
        "required_tools": tools_needed,
        "reasons": reasons,
        "role": agent.get("role"),
        "source": agent.get("_source") or "agentx",
    }


def list_agent_tools_tools() -> Dict[str, Any]:
    reg, ToolRegistry, err = _agent_tools_pkg()
    if ToolRegistry is None:
        return {"ok": False, "error": err or "agent_tools unavailable"}
    try:
        wired = ToolRegistry.auto_wire()
        tools = [
            {
                "name": t.name,
                "description": t.description,
                "safety": t.safety,
                "input_required": (t.input_schema or {}).get("required") or [],
            }
            for t in wired.list_tools()
        ]
        return {"ok": True, "count": len(tools), "tools": tools}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def invoke_agent_tool(
    tool: str,
    payload: Optional[Dict[str, Any]] = None,
    profile: str = "balanced",
    dry_run: bool = True,
    allowed_tools: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Invoke a gold tooling tool under profile constraints."""
    reg, ToolRegistry, err = _agent_tools_pkg()
    if ToolRegistry is None or reg is None:
        return {"ok": False, "error": err or "agent_tools unavailable"}
    payload = dict(payload or {})
    tool = (tool or "").strip() or "filesystem"
    if tool == "filesystem":
        payload.setdefault("operation", "list")
        payload.setdefault("path", ".")
    if allowed_tools:
        allowed = [str(x) for x in allowed_tools]
    else:
        pname = (profile or "balanced").lower()
        if pname == "strict":
            pname = "safe"
        if pname == "open":
            pname = "power"
        try:
            profiles = reg.load_profiles()
            prof = profiles.get(pname)
            if prof:
                allowed = list(prof.tools) + ["filesystem", "http", "crypto", "solana"]
            else:
                allowed = ["filesystem", "http"]
        except Exception:
            allowed = ["filesystem", "http"]
        if pname in ("balanced", "power", "open"):
            for n in ("filesystem", "http", "crypto", "solana"):
                if n not in allowed:
                    allowed.append(n)
        if pname in ("safe", "strict"):
            allowed = ["filesystem"]
    if dry_run is None:
        dry_run = True
    try:
        wired = ToolRegistry.auto_wire()
        name = tool
        if name in ("read_file", "list_dir") and wired.get("filesystem"):
            name = "filesystem"
            if "operation" not in payload:
                payload = {
                    **payload,
                    "operation": "read" if tool == "read_file" else "list",
                    "path": payload.get("path")
                    or payload.get("target_file")
                    or payload.get("target_directory")
                    or ".",
                }
        result = wired.invoke(
            name, payload, allowed_tools=allowed, dry_run=bool(dry_run)
        )
        return {
            "ok": True,
            "tool": name,
            "profile": profile,
            "dry_run": bool(dry_run),
            "result": result,
        }
    except PermissionError as e:
        return {"ok": False, "error": str(e), "tool": tool, "allowed": allowed}
    except Exception as e:
        return {"ok": False, "error": str(e), "tool": tool}


def orch_health(timeout: float = 1.5) -> Dict[str, Any]:
    """GET orchestrator /health. Returns {ok, url, body|error}."""
    url = ORCH_BASE.rstrip("/") + "/health"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                body = raw[:500]
            return {"ok": True, "url": url, "status": resp.status, "body": body}
    except Exception as e:
        return {"ok": False, "url": url, "error": str(e)}


def vulkan_health(timeout: float = 1.5) -> Dict[str, Any]:
    url = VULKAN_BASE.rstrip("/") + "/health"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                body = raw[:500]
            return {"ok": True, "url": url, "status": resp.status, "body": body}
    except Exception as e:
        return {"ok": False, "url": url, "error": str(e)}


class _VulkanChatClient:
    """Chat client: prefer live orchestrator :8001, then raw Vulkan :8080."""

    def __init__(self, base: Optional[str] = None, model: Optional[str] = None):
        self.base = (base or VULKAN_BASE).rstrip("/")
        self.model = model or BACKEND_MODEL

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 384,
        temperature: float = 0.3,
        direct_vulkan: bool = False,
    ) -> Dict[str, Any]:
        # ONLINE default: orchestrator first whenever it is up (or forced).
        # direct_vulkan=True skips :8001 so hive planner/worker/critic are not
        # swallowed by live_exec / tool middleware on the gateway.
        force = (os.environ.get("REALAI_BRIDGE_USE_ORCH") or "auto").strip().lower()
        orch_up = force in ("1", "true", "yes", "on") or (
            force == "auto" and orch_health(0.8).get("ok")
        )
        targets: List[tuple] = []
        if direct_vulkan:
            targets.append((self.base + "/v1/chat/completions", model or self.model))
        else:
            if orch_up:
                targets.append((ORCH_BASE + "/v1/chat/completions", model or DEFAULT_MODEL))
            targets.append((self.base + "/v1/chat/completions", model or self.model))
            if not orch_up:
                targets.append((ORCH_BASE + "/v1/chat/completions", model or DEFAULT_MODEL))
        last_err = None
        for url, mid in targets:
            body = json.dumps(
                {
                    "model": mid,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": False,
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer "
                    + (os.environ.get("REALAI_API_KEY") or "local"),
                    "X-RealAI-Tools": "off",
                    "X-RealAI-Voice": "off",
                    "X-RealAI-Memory": "off",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=180) as resp:
                    return json.loads(resp.read().decode("utf-8", errors="replace"))
            except Exception as e:
                last_err = e
                continue
        return {
            "ok": False,
            "error": f"chat_backend_unavailable: {last_err}",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                    }
                }
            ],
        }


_PWC_PROMPTS = {
    "planner": (
        "You are the RealAI HIVE PLANNER (multi-agent orchestration on local Vulkan). "
        "RealAI 'hive' means the local agent swarm (overseer/coder/architect/...), "
        # drift guard merged 2026-10-16 from the archive phase (MERGE_LEDGER: v3_runtime_bridge _PWC_PROMPTS)
        "NOT Apache Hive, NOT Hadoop, NOT Hive CLI, NOT Hiveserver2: "
        "never emit Apache/Hadoop install or SQL-warehouse steps unless the user explicitly wrote 'Apache Hive' or 'Hadoop'. "
        "Produce a short numbered plan (3-5 steps). "
        "If the task names a workspace file, step 1 MUST be workspace_read on that path. "
        "Never claim LANDED unless a tool write already succeeded. Prefer PROPOSED."
    ),
    "worker": (
        "You are the RealAI HIVE WORKER. You receive REAL probe JSON and any workspace_read "
        "results already executed. Quote real file content when a read is present. "
        "Do not invent file contents. Do not say LANDED. Forbidden: Apache Hive fluff "
        "(Hadoop, Hive CLI, Hiveserver2, Beeline, warehouse SQL setup)."
    ),
    "critic": (
        "You are the RealAI HIVE CRITIC. "
        "If the task is read/quote/plan and workspace_read succeeded, verdict Pass. "
        "Fail only if a named file was unread, or a write/edit/patch was requested without a tool write. "
        "Never Fail a successful read-only quote for lacking a write. Prefer PROPOSED over LANDED."
    ),
}


def _extract_workspace_paths(task: str) -> List[str]:
    """Pull likely repo-relative paths from a task string."""
    text = (task or "").replace("\\", "/")
    found: List[str] = []

    def _add(p: str) -> None:
        p = (p or "").replace("\\", "/").strip().strip("\"'")
        if not p:
            return
        # Map absolute product paths to repo-relative
        low = p.lower()
        for prefix in (
            "c:/realai-clean/",
            "/realai-clean/",
        ):
            if low.startswith(prefix):
                p = p[len(prefix):] if len(p) >= len(prefix) else p
                low = p.lower()
                break
        # Bare console.html → gold webview (product twin is synced)
        if "/" not in p and p.lower() == "console.html":
            p = "apps/vscode/webview/console.html"
        if "/" not in p and p.lower() == "readme.md":
            p = "apps/vscode/README.md"
        if p not in found:
            found.append(p)

    for m in re.finditer(
        r"(?<![\w./-])((?:apps|realai|modules|abilities|docs|scripts|frontend|agents|fusion-ui|\.github)/[\w./\-]+\.[\w]+)",
        text,
        flags=re.I,
    ):
        _add(m.group(1))
    # Absolute Windows / POSIX under RealAI-clean
    for m in re.finditer(
        r"(?<![\w])([A-Za-z]:/RealAI-clean/[\w./\-]+\.[\w]+)",
        text,
        flags=re.I,
    ):
        _add(m.group(1))
    for m in re.finditer(r"\bread\s+([\w./\-]+\.[\w]+)", text, flags=re.I):
        _add(m.group(1))
    # Bare known UI/config filenames named in the task
    for m in re.finditer(
        r"(?<![\w./-])(console\.html|package\.json|realai\.toml|models\.yaml|model\.json)\b",
        text,
        flags=re.I,
    ):
        _add(m.group(1))
    if not found and re.search(r"apps[/\\]vscode[/\\]README\.md", text, re.I):
        _add("apps/vscode/README.md")
    return found[:5]


def _task_names_a_path(task: str) -> bool:
    """True when the task mentions a file path (even if extraction missed)."""
    text = (task or "").replace("\\", "/")
    if _extract_workspace_paths(task):
        return True
    if re.search(r"[A-Za-z]:/RealAI-clean/[\w./\-]+", text, re.I):
        return True
    if re.search(
        r"(?<![\w./-])(?:apps|realai|modules|abilities|docs|scripts|frontend|agents|fusion-ui)/[\w./\-]+",
        text,
        re.I,
    ):
        return True
    if re.search(r"(?<![\w./-])console\.html\b", text, re.I):
        return True
    return False


def _workspace_reads_for_task(task: str) -> Dict[str, Any]:
    """Execute workspace_read for paths named in the task (before LLM stages)."""
    paths = _extract_workspace_paths(task)
    reads: List[Dict[str, Any]] = []
    ok_any = False
    for path in paths:
        result = workspace_tool("workspace_read", {"path": path, "start": 1, "limit": 40})
        ok = False
        snippet = ""
        if isinstance(result, dict):
            if result.get("error"):
                ok = False
            elif result.get("ok") is False:
                ok = False
            elif result.get("content") or result.get("text") or result.get("lines"):
                ok = True
            elif result.get("ok") is True:
                ok = True
            snippet = str(
                result.get("content")
                or result.get("text")
                or "\n".join(result.get("lines") or [])
                or ""
            )[:2000]
        ok_any = ok_any or ok
        reads.append({"path": path, "ok": ok, "result": result, "snippet": snippet})
    named = bool(paths) or _task_names_a_path(task)
    return {
        "paths": paths,
        "reads": reads,
        "ok": (ok_any if paths else (False if named else True)),
        "required": named,
        "named_path": named,
    }



def _task_requests_write(task: str) -> bool:
    """True only for explicit write/apply/commit intents — not propose/quote/read."""
    low = (task or "").lower()
    # Explicit non-write / proposal language wins
    if re.search(r"\bdo\s+not\s+(?:workspace_)?write\b", low):
        return False
    if re.search(r"\b(?:don'?t|do\s+not)\s+write\b", low):
        return False
    propose_keys = (
        "propose", "suggest", "quote", "read", "first n lines", "as a proposal",
        "css change as proposal", "do not write", "do not workspace_write",
    )
    # Quote / propose / suggest CSS tweak without apply → not a write
    if re.search(r"\b(propose|suggest|quote)\b", low) and not re.search(
        r"\b(workspace_write|overwrite|apply|commit|save\s+file|write\s+to)\b", low
    ):
        return False
    if re.search(r"\b(read|first\s+\d+\s+lines)\b", low) and not re.search(
        r"\b(workspace_write|overwrite|apply|commit|save\s+file|write\s+to)\b", low
    ):
        return False
    true_keys = (
        "workspace_write",
        "overwrite",
        "save file",
        "write to",
    )
    if any(k in low for k in true_keys):
        return True
    # standalone apply / commit (not "apply to thinking")
    if re.search(r"\bapply\b", low) and not re.search(r"\bpropose\b", low):
        return True
    if re.search(r"\bcommit\b", low):
        return True
    return False

def _scrub_landed(text: str, write_ok: bool = False) -> str:
    if write_ok or not text:
        return text
    return re.sub(r"\bLANDED\b", "PROPOSED", text, flags=re.I)

def _collect_worker_probes(task: str) -> Dict[str, Any]:
    """Run real local probes for the multi-agent worker stage (no invented stdout)."""
    probes: Dict[str, Any] = {
        "task": (task or "")[:500],
        "orch": orch_health(),
        "vulkan": vulkan_health(),
    }
    for key, path in (
        ("hive", "/v1/hive"),
        ("agents", "/v1/agents"),
        ("capabilities", "/v1/capabilities"),
        ("tools", "/v1/tools"),
    ):
        try:
            import urllib.request

            url = f"{ORCH_BASE}{path}"
            req = urllib.request.Request(url, headers={"User-Agent": "RealAI-multi-worker/1.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                try:
                    body = json.loads(raw)
                except Exception:
                    body = {"raw": raw[:800]}
                probes[key] = {"ok": True, "status": getattr(resp, "status", 200), "body": body}
        except Exception as exc:
            probes[key] = {"ok": False, "error": str(exc)}
    try:
        agents_body = (probes.get("agents") or {}).get("body") or {}
        rows = agents_body if isinstance(agents_body, list) else (agents_body.get("data") or [])
        ids = []
        for row in (rows or [])[:40]:
            if isinstance(row, dict) and row.get("id"):
                ids.append(str(row["id"]))
            elif isinstance(row, str):
                ids.append(row)
        probes["agent_ids_sample"] = ids
        probes["agents_count"] = len(rows) if isinstance(rows, list) else len(ids)
    except Exception:
        pass
    return probes


def _format_worker_probe_report(probes: Dict[str, Any]) -> str:
    lines = ["[RealAI multi_agent worker — REAL probes, not invented]", ""]
    orch = probes.get("orch") or {}
    vulk = probes.get("vulkan") or {}
    lines.append(
        f"orchestrator :8001 -> ok={bool(orch.get('ok'))} status={orch.get('status')} url={orch.get('url')}"
    )
    lines.append(
        f"vulkan :8080 -> ok={bool(vulk.get('ok'))} status={vulk.get('status')} url={vulk.get('url')}"
    )
    for key in ("hive", "agents", "capabilities", "tools"):
        row = probes.get(key) or {}
        if row.get("ok"):
            body = row.get("body")
            try:
                size = len(json.dumps(body, default=str))
            except Exception:
                size = 0
            extra = ""
            if key == "agents":
                extra = (
                    f" count={probes.get('agents_count', '?')}"
                    f" sample={probes.get('agent_ids_sample', [])[:8]}"
                )
            lines.append(f"GET {key} -> ok status={row.get('status')} bytes~{size}{extra}")
        else:
            lines.append(f"GET {key} -> FAIL {row.get('error')}")
    lines.append("")
    lines.append(f"task: {probes.get('task') or ''}")
    return "\n".join(lines)



def _stage_text(resp: Dict[str, Any]) -> str:
    try:
        return (
            ((resp.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        ).strip()
    except Exception:
        return ""


BRIDGE_MULTI_REVISION = "2026-09-21-critic-propose-neq-write-v3"

def _is_apps_vscode_patch_task(task: str) -> bool:
    """True when the user asked for concrete apps/vscode file patches (not health fluff)."""
    low = (task or "").lower()
    if "apps/vscode" not in low and "apps\\vscode" not in low and "realai-vscode" not in low:
        return False
    return any(
        k in low
        for k in (
            "patch",
            "patches",
            "/patches",
            "audit",
            "concrete",
            "extension",
            "webview",
            "lmchat",
            "consolepanel",
        )
    )


def _vscode_patch_task_addon(task: str) -> str:
    if not _is_apps_vscode_patch_task(task):
        return ""
    return (
        "\n\nHARD RULES FOR THIS TASK (AtomicFizz / RealAI):\n"
        "- Output ONLY concrete patches with exact paths under apps/vscode/ "
        "(or docs/sessions/PHASES.md for stage tip).\n"
        "- Prefer the deterministic auditor pattern: name file, Change, Why, PROPOSED (use LANDED only after a real tool write succeeded).\n"
        "- FORBIDDEN: Live Share, marketplace installs, 'update VS Code', generic multi-agent fluff, "
        "agent-count health essays, 'monitor 245 agents', stack restart checklists as the answer.\n"
        "- Stack health may be assumed from REAL probes; do not make health the deliverable.\n"
        "- If you cannot name real files, say: use Console /patches (deterministic auditor).\n"
    )



def _run_planner_worker_critic(
    task: str,
    client: "_VulkanChatClient",
    max_tokens: int = 384,
    temperature: float = 0.3,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Live Vulkan-backed planner → worker → critic (via orchestrator chat when up)."""
    import time

    t0 = time.time()
    ctx_blob = ""
    if context:
        try:
            ctx_blob = "\nContext:\n" + json.dumps(context, default=str)[:2000]
        except Exception:
            ctx_blob = f"\nContext:\n{context}"

    stages: Dict[str, str] = {}
    errors: Dict[str, str] = {}

    # Deterministic workspace_read BEFORE planner/worker invent content
    file_reads = _workspace_reads_for_task(task)
    write_ok = False
    read_blob = ""
    if file_reads.get("reads"):
        parts = []
        for r in file_reads["reads"]:
            parts.append(
                f"### workspace_read path={r.get('path')} ok={r.get('ok')}\n"
                f"{(r.get('snippet') or '')[:1500]}"
            )
        read_blob = "\n\nFILE READS (real disk):\n" + "\n\n".join(parts)
    ctx_blob = (ctx_blob or "") + read_blob

    # PLANNER
    plan_resp = client.chat_completion(
        [
            {"role": "system", "content": _PWC_PROMPTS["planner"]},
            {"role": "user", "content": f"Task:\n{task}{ctx_blob}{_vscode_patch_task_addon(task)}"},
        ],
        model=DEFAULT_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        direct_vulkan=True,
    )
    if plan_resp.get("error"):
        errors["planner"] = str(plan_resp.get("error"))
    stages["planner"] = _stage_text(plan_resp)
    if not stages["planner"]:
        return {
            "ok": False,
            "mode": "pipeline",
            "error": "planner_empty",
            "binding": errors or plan_resp.get("error") or "no planner content",
            "orch": orch_health(),
            "vulkan": vulkan_health(),
            "source": "realai.v3_runtime_bridge.planner_worker_critic",
        }

    # WORKER — real probes first, then short LLM summary grounded in those facts
    probes = _collect_worker_probes(task)
    probes["file_reads"] = file_reads
    probe_report = _format_worker_probe_report(probes)
    if read_blob:
        probe_report = probe_report + "\n\n" + read_blob.strip()
    work_resp = client.chat_completion(
        [
            {"role": "system", "content": _PWC_PROMPTS["worker"]},
            {
                "role": "user",
                "content": (
                    f"Task:\n{task}{_vscode_patch_task_addon(task)}\n\nPlanner output:\n{stages['planner']}\n\n"
                    f"REAL probe report:\n{probe_report}\n\n"
                    f"Probe JSON (trim):\n{json.dumps({k: probes.get(k) for k in ('orch','vulkan','agents_count','agent_ids_sample','hive') if k in probes}, default=str)[:2500]}"
                    f"{ctx_blob}"
                ),
            },
        ],
        model=DEFAULT_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        direct_vulkan=True,
    )
    if work_resp.get("error"):
        errors["worker"] = str(work_resp.get("error"))
    summary = _stage_text(work_resp)
    # Always keep the real probe report; append model summary when present
    if summary and "I only report REAL process output" not in summary:
        stages["worker"] = probe_report + "\n\n## Worker summary\n" + summary
    else:
        stages["worker"] = probe_report
        if summary:
            stages["worker"] += "\n\n## Worker model note\n" + summary[:800]
    if not stages["worker"].strip():
        return {
            "ok": False,
            "mode": "pipeline",
            "stage_outputs": stages,
            "error": "worker_empty",
            "binding": errors or work_resp.get("error") or "no worker content",
            "orch": orch_health(),
            "vulkan": vulkan_health(),
            "source": "realai.v3_runtime_bridge.planner_worker_critic",
            "probes": probes,
        }

    # CRITIC
    crit_resp = client.chat_completion(
        [
            {"role": "system", "content": _PWC_PROMPTS["critic"]},
            {
                "role": "user",
                "content": (
                    f"Task:\n{task}{_vscode_patch_task_addon(task)}\n\nPlanner:\n{stages['planner']}\n\n"
                    f"Worker:\n{stages['worker']}{ctx_blob}"
                ),
            },
        ],
        model=DEFAULT_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        direct_vulkan=True,
    )
    if crit_resp.get("error"):
        errors["critic"] = str(crit_resp.get("error"))
    stages["critic"] = _stage_text(crit_resp)
    if (not stages["critic"]) or ("I only report REAL process output" in stages["critic"]) or (
        "[RealAI live_exec" in stages["critic"] and "hostname" in stages["critic"] and len(stages["critic"]) < 400
    ):
        orch_ok = bool((probes.get("orch") or {}).get("ok"))
        vulk_ok = bool((probes.get("vulkan") or {}).get("ok"))
        n_agents = probes.get("agents_count")
        verdict = "pass" if orch_ok and vulk_ok else "fail"
        stages["critic"] = (
            f"[RealAI critic — grounded in REAL probes]\n"
            f"verdict: {verdict}\n"
            f"- orchestrator ok={orch_ok}\n"
            f"- vulkan ok={vulk_ok}\n"
            f"- agents_count={n_agents}\n"
            f"- planner_steps_present={bool(stages.get('planner'))}\n"
            f"- gaps: prefer console Ops→Hive for runs; keep agents-ui watch-only; "
            f"avoid generic 'sync all repos' unless task asks for git.\n"
            f"- next: re-run multi_agent_run after gateway reload if worker summary still looks like live_exec help."
        )

    
    # Hard scrub: never ship live_exec help / hostname blurb as hive stages
    _HELP = "I only report REAL process output"
    if _HELP in (stages.get("worker") or "") and "REAL probes" not in (stages.get("worker") or ""):
        stages["worker"] = probe_report or stages["worker"]
    if "[RealAI live_exec" in (stages.get("critic") or "") and "hostname" in (stages.get("critic") or ""):
        stages["critic"] = (
            "[RealAI critic - grounded in REAL probes]\n"
            f"- orch_ok={bool((probes.get("orch") or {}).get("ok"))}\n"
            f"- vulkan_ok={bool((probes.get("vulkan") or {}).get("ok"))}\n"
            f"- agents={probes.get("agent_count")}\n"
            "- live_exec hostname blurb discarded (not a code review)."
        )

    
    if _is_apps_vscode_patch_task(task):
        fluff = ("245 agents", "agent coverage", "agent diversity", "agent updates", "monitor the performance")
        for key in ("planner", "worker", "critic"):
            body = stages.get(key) or ""
            low = body.lower()
            looks_fluff = sum(1 for f in fluff if f in low) >= 2 or (
                "apps/vscode" not in low
                and "patch" not in low
                and key in ("planner", "critic")
                and "health" in low
            )
            if looks_fluff or (key == "critic" and "verdict" in low and "apps/vscode/" not in body and "apps/vscode" not in low):
                stages[key] = (
                    (probe_report + "\n\n" if key == "worker" and "REAL probes" in (probe_report or "") else "")
                    + f"[RealAI {key} — apps/vscode patch task]\n"
                    "This task requires concrete patches under apps/vscode/ only.\n"
                    "Do not treat stack health / agent-count as the deliverable.\n"
                    "Use Console slash /patches (deterministic auditor: auditAppsVscode) "
                    "or name exact files e.g. apps/vscode/src/*.ts, webview/*, package.json.\n"
                    "Forbidden: Live Share, marketplace, update VS Code, generic multi-agent fluff."
                )



    # Deterministic critic verdict (do not trust LLM drift on read-only)
    wants_write = _task_requests_write(task)
    write_ok = bool(write_ok)
    if file_reads.get("required") and not file_reads.get("ok"):
        pass  # handled below as hard fail
    elif wants_write and not write_ok:
        stages["critic"] = (
            "[RealAI critic — FAIL]\n"
            "verdict: fail\n"
            "reason: task requested edit/patch/write/commit but no workspace_write succeeded.\n"
        )
    elif (not wants_write) and (file_reads.get("ok") or not file_reads.get("required")):
        # Read/quote/plan (or no file named): Pass when reads ok / not required
        quote_bits = []
        for r in (file_reads.get("reads") or []):
            if r.get("ok") and r.get("snippet"):
                first = (r.get("snippet") or "").splitlines()[:2]
                quote_bits.append(" / ".join(first)[:200])
        stages["critic"] = (
            "[RealAI critic — grounded]\n"
            "verdict: pass\n"
            "reason: read-only task with successful workspace_read (or no file required); "
            "tool write not required.\n"
            + (f"quoted: {quote_bits[0]}\n" if quote_bits else "")
        )


    # Hard fail: named file but no successful workspace_read
    if file_reads.get("required") and not file_reads.get("ok"):
        stages["critic"] = (
            "[RealAI critic — FAIL]\n"
            "verdict: fail\n"
            "reason: named path but no workspace_read\n"
            f"paths={file_reads.get('paths')}\n"
        )
        return {
            "ok": False,
            "mode": "pipeline",
            "planner": _scrub_landed(stages.get("planner") or "", write_ok),
            "worker": _scrub_landed(stages.get("worker") or "", write_ok),
            "critic": stages["critic"],
            "stage_outputs": {k: _scrub_landed(v, write_ok) for k, v in stages.items()},
            "final_output": _scrub_landed(
                f"## Planner\n{stages.get('planner')}\n\n## Worker\n{stages.get('worker')}\n\n## Critic\n{stages['critic']}",
                write_ok,
            ),
            "error": "workspace_read_required",
            "file_reads": file_reads,
            "duration_ms": int((time.time() - t0) * 1000),
            "source": "realai.v3_runtime_bridge.planner_worker_critic",
            "bridge_revision": BRIDGE_MULTI_REVISION,
        }

    # Scrub LANDED from stage text unless a write succeeded
    for _k in list(stages.keys()):
        stages[_k] = _scrub_landed(stages.get(_k) or "", write_ok)

    final = (
        f"## Planner\n{stages['planner']}\n\n"
        f"## Worker\n{stages['worker']}\n\n"
        f"## Critic\n{stages.get('critic') or '(empty)'}"
    )
    return {
        "ok": bool(stages.get("critic")),
        "mode": "pipeline",
        "planner": stages["planner"],
        "worker": stages["worker"],
        "critic": stages.get("critic") or "",
        "stage_outputs": stages,
        "final_output": final,
        "duration_ms": int((time.time() - t0) * 1000),
        "errors": errors or None,
        "probes": {
            "orch_ok": bool((probes.get("orch") or {}).get("ok")),
            "vulkan_ok": bool((probes.get("vulkan") or {}).get("ok")),
            "agents_count": probes.get("agents_count"),
            "agent_ids_sample": probes.get("agent_ids_sample"),
            "file_reads": file_reads,
        },
        "file_reads": file_reads,
        "orch": orch_health(),
        "vulkan": vulkan_health(),
        "source": "realai.v3_runtime_bridge.planner_worker_critic",
        "bridge_revision": BRIDGE_MULTI_REVISION,
        "api_base": ORCH_BASE,
        "vulkan_base": VULKAN_BASE,
    }


def run_multi_agent(
    task: str,
    mode: str = "pipeline",
    max_tokens: int = 384,
    temperature: float = 0.3,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Live multi-agent pipeline for the orchestrator.

    Requires ONLINE orchestrator (:8001) and Vulkan (:8080).
    Does NOT use single-agent / offline fallback text.
    """
    task = (task or "").strip()
    if not task:
        return {"ok": False, "error": "empty_task"}

    oh = orch_health()
    vh = vulkan_health()
    if not oh.get("ok"):
        return {
            "ok": False,
            "error": "orchestrator_offline",
            "binding": f"GET {oh.get('url')} failed: {oh.get('error')}",
            "orch": oh,
            "vulkan": vh,
            "hint": "Start: python -m realai.v3_orchestrator --host 127.0.0.1 --port 8001",
        }
    if not vh.get("ok"):
        return {
            "ok": False,
            "error": "vulkan_offline",
            "binding": f"GET {vh.get('url')} failed: {vh.get('error')}",
            "orch": oh,
            "vulkan": vh,
            "hint": "Start Vulkan llama-server on :8080",
        }

    mode = (mode or "pipeline").lower()
    client = _VulkanChatClient()
    if mode == "parallel":
        return _run_parallel_agents(
            task, client, max_tokens=max_tokens, temperature=temperature
        )
    return _run_planner_worker_critic(
        task,
        client,
        max_tokens=max_tokens,
        temperature=temperature,
        context=context,
    )


def _run_parallel_agents(
    task: str,
    client: _VulkanChatClient,
    max_tokens: int = 384,
    temperature: float = 0.3,
) -> Dict[str, Any]:
    agents = _load_agents()
    picks = []
    for a in agents:
        if not isinstance(a, dict):
            continue
        if str(a.get("risk_level") or "low").lower() in ("low", "medium", "none"):
            picks.append(a)
        if len(picks) >= 3:
            break
    if not picks:
        picks = [a for a in agents[:3] if isinstance(a, dict)]
    outputs = []
    for a in picks:
        role = a.get("role") or a.get("id")
        system = (
            f"You are agent {a.get('id')} — {role}. "
            f"Capabilities: {', '.join((a.get('capabilities') or [])[:8])}. "
            "Respond with a concise specialist take."
        )
        resp = client.chat_completion(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": task},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        content = (
            ((resp.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        )
        outputs.append({"agent_id": a.get("id"), "role": role, "content": content})
    synth_in = "Task: " + task + "\n\n" + "\n\n".join(
        f"### {o['agent_id']}\n{o['content']}" for o in outputs
    )
    synth = client.chat_completion(
        [
            {
                "role": "system",
                "content": "Synthesize specialist outputs into one clear final answer.",
            },
            {"role": "user", "content": synth_in},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    final = (
        ((synth.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    )
    return {
        "ok": True,
        "mode": "parallel",
        "final_output": final,
        "agent_outputs": outputs,
        "source": "v3_runtime_bridge.parallel",
    }


def _invoke_ability_run(
    run_fn: Any,
    *,
    aid: str,
    raw_input: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Call ability run() with either (input, context) or RackUp (player, payload) signatures."""
    import inspect

    context = dict(context or {})
    sig = inspect.signature(run_fn)
    params = sig.parameters
    accepts_var_kw = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
    )

    if accepts_var_kw or ("input" in params and "context" in params) or (
        "input" in params and accepts_var_kw
    ):
        return run_fn(input=raw_input, context=context)

    if "player" in params:
        from plugins.rackup_coach.types import PlayerProfile

        pdata = context.get("player") if isinstance(context.get("player"), dict) else None
        if not pdata:
            pdata = {
                "player_id": str(context.get("player_id") or "hive"),
                "display_name": str(context.get("display_name") or ""),
            }
            if "rating" in context:
                pdata["rating"] = context.get("rating")
            if "discipline" in context:
                pdata["discipline"] = context.get("discipline")
        player = PlayerProfile(player_id=str(pdata.get("player_id") or "hive"))
        for field_name in (
            "display_name",
            "rating",
            "rd",
            "volatility",
            "rating_system",
            "discipline",
            "preferred_hand",
            "hall_id",
            "hall_name",
            "table_speed",
            "table_size",
            "pyramid_skill",
            "skill_level",
        ):
            if field_name in pdata and pdata[field_name] not in (None, ""):
                try:
                    setattr(player, field_name, pdata[field_name])
                except Exception:
                    pass
        payload = context.get("payload") if isinstance(context.get("payload"), dict) else None
        if payload is None:
            payload = {
                k: v
                for k, v in context.items()
                if k not in ("player", "player_id", "payload", "goal")
            }
            if raw_input and "text" not in payload and "question" not in payload:
                payload["input"] = raw_input
                payload["question"] = raw_input
        kwargs: Dict[str, Any] = {}
        if "payload" in params:
            kwargs["payload"] = payload
        if "goal" in params:
            kwargs["goal"] = str(context.get("goal") or raw_input or "")
        out = run_fn(player, **kwargs)
        if isinstance(out, dict):
            out.setdefault("ok", True)
            out.setdefault("ability", aid)
        return out if isinstance(out, dict) else {"ok": True, "ability": aid, "result": out}

    # Last resort: try input/context, then bare call
    try:
        return run_fn(input=raw_input, context=context)
    except TypeError:
        try:
            return run_fn(raw_input, context)
        except TypeError:
            return run_fn()


def execute_registry_tool(
    name: str, arguments: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Execute TOOL_REGISTRY / workspace / core.tools tools locally."""
    arguments = arguments or {}
    name = (name or "").strip()

    # Bare surface / ability names from /v1/tools → ability.* handlers
    _BARE_ABILITY = {
        "agents_surface",
        "agent_tools_surface",
        "plugins_surface",
        "core_surface",
        "modules_surface",
        "orchestration_surface",
        "repo_surface",
        "omnibrain",
        "world_brain",
        "overseer",
        "hive_orchestrator",
        "nest_orchestrators",
        "cli_surface",
        "device_selector",
        "memory_learning",
        "knowledge_synthesis",
        "observability_self_improve",
        "audio_transcription",
        "audio_speech",
        "voice_streaming",
        "image_analysis",
        "image_generation",
        "video_generation",
        "coach",
        "shot_of_the_day",
        "rating_update",
        "tournament",
        "ledger_audit",
        "matchmaking",
        "web3_integration",
        "code_engineer_agent",
        "hierarchical_specialists",
        "game_world",
        "organs_hive",
        "plugin_system",
        "learn_git",
        "self_reflection",
        "multi_agent",
        "desktop_lambda_chat",
        "desktop_lambda_image",
        "desktop_lambda_video",
        "desktop_lambda_advanced",
        "overmind_runner",
        "deep_promote",
        "approval_store",
        "code_engineer_cli",
        "harden_repos",
        "rollout_all_repos",
        "quarantine_reconstruct",
        "local_inference",
        "training_pipeline",
        "lora_adapters",
        "kilo_recovery",
        "frontend_ui",
        "hive_governance",
        "hominis_enterprise",  # alias → abilities.hominis_enterprise → hive_governance
        "chat_completion",
        "text_generation",
        "code_generation",
        "embeddings",
        "translation",
        "task_automation",
        "business_planning",
        "therapy_counseling",
        "hall_context",
        "league_validate",
        "moderation",
        "money_anomaly",
        "payout_sanity",
        "pyramid_rules",
        "rating_convert",
        "rating_intel",
        "sotd_contribute",
        "video_analysis",
        "ttt9d_move",
        "pr_triage",
        "vuln_triage",
        "ci_failure_classify",
    }
    if name in _BARE_ABILITY:
        name = "ability." + name

    # File / shell helpers advertised in catalog
    if name in ("run_terminal_command", "run_command", "shell"):
        try:
            from realai.bot.live_exec import run_command

            cmd = str(arguments.get("command") or arguments.get("cmd") or "").strip()
            if not cmd:
                cmd = "echo realai-ok"
            return run_command(cmd)
        except Exception as e:
            return {"ok": False, "error": str(e), "tool": name}
    if name in ("read_file", "workspace_read"):
        return workspace_tool("workspace_read", arguments)
    if name in ("list_dir", "workspace_list"):
        return workspace_tool("workspace_list", arguments)
    if name == "search_replace":
        # Same confinement as workspace_write (Security #210): no craft fallback, REALAI_TOOLS_ALLOW required.
        path = arguments.get("path") or arguments.get("file") or ""
        old = arguments.get("old_string") or arguments.get("old")
        new = arguments.get("new_string") or arguments.get("new") or arguments.get("content")
        if old is not None and new is not None and path:
            if not _ws_write_allowed():
                return {"ok": False, "error": "write_not_allowed", "tool": name}
            try:
                root = workspace_root()
                parts = ws_parts(path)
                data = ws_read_bytes(root, parts, WS_MAX_READ_BYTES)
                if _ws_is_binary(data):
                    return {"ok": False, "error": "binary_not_allowed", "tool": name}
                text = data.decode("utf-8", errors="replace")
                if str(old) not in text:
                    return {"ok": False, "error": "old_string_not_found", "tool": name}
                return workspace_tool("workspace_write", {"path": path, "content": text.replace(str(old), str(new), 1)})
            except WorkspacePathError as e:
                return {"ok": False, "error": e.code, "tool": name}
            except OSError:
                return {"ok": False, "error": "io_error", "tool": name}
        return workspace_tool(
            "workspace_write",
            {
                "path": path,
                "content": new if new is not None else arguments.get("content"),
            },
        )
    if name == "workspace_grep" or name == "grep":
        return workspace_tool("workspace_grep", arguments)
    if name in ("git", "git_status"):
        try:
            from realai.cli.craft import apply_workspace, tool_git_status

            apply_workspace()
            out = tool_git_status()
            if isinstance(out, dict):
                out.setdefault("ok", not bool(out.get("error")))
                out["tool"] = "git_status"
                return out
            return {"ok": False, "error": "bad_git_status", "tool": "git_status"}
        except Exception as e:
            return {"ok": False, "error": str(e), "tool": "git_status"}
    if name in ("git_diff", "diff"):
        try:
            from realai.cli.craft import apply_workspace, tool_git_diff

            apply_workspace()
            out = tool_git_diff(str(arguments.get("path") or ""))
            if isinstance(out, dict):
                out.setdefault("ok", not bool(out.get("error")))
                out["tool"] = "git_diff"
                return out
            return {"ok": False, "error": "bad_git_diff", "tool": "git_diff"}
        except Exception as e:
            return {"ok": False, "error": str(e), "tool": "git_diff"}
    if name in ("learn_status", "learn_packets"):
        try:
            from realai.learn.http import list_packets

            out = list_packets()
            rows = out.get("packets") if isinstance(out, dict) else None
            rows = rows if isinstance(rows, list) else []
            slugs: List[str] = []
            for row in rows[:20]:
                if isinstance(row, dict) and row.get("slug"):
                    slugs.append(str(row.get("slug")))
                elif isinstance(row, str):
                    slugs.append(row)
            return {
                "ok": True,
                "tool": name,
                "count": len(rows),
                "slugs": slugs,
                "note": (
                    "Learn status via packet list. "
                    "POST /v1/learn/queue is not auto-run from the core desk."
                ),
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "tool": name}

    # --- core.* → core.tools.ToolRegistry ---
    if name.startswith("core.") or name in ("code_exec", "web_search"):
        core_name = name.split(".", 1)[-1] if name.startswith("core.") else name
        reg = _core_tool_registry()
        if not reg:
            return {"ok": False, "error": "core_tools_unavailable"}
        args = dict(arguments or {})
        # Smoke-friendly defaults for file_tool
        if core_name == "file_tool":
            args.setdefault("action", "read")
            if not str(args.get("path") or "").strip():
                args["path"] = "README.md"
        allowed = ["NETWORK"]
        if core_name == "code_exec":
            allowed.append("CODE_EXEC")
        if core_name in ("file_tool", "file"):
            allowed.append("FILESYSTEM")
        try:
            from core.tools.permissions import Permissions

            ctx_allowed: List[Any] = list(allowed)
            for attr in ("NETWORK", "CODE_EXEC", "FILESYSTEM", "FS_READ", "FS_WRITE"):
                if hasattr(Permissions, attr) and attr in allowed:
                    ctx_allowed.append(getattr(Permissions, attr))
            result = reg.execute_tool(
                core_name,
                args,
                context={"allowed_permissions": ctx_allowed},
            )
            return {
                "ok": True,
                "tool": f"core.{core_name}",
                "result": result,
                "source": "core.tools",
            }
        except PermissionError as e:
            return {"ok": False, "error": str(e), "tool": name}
        except KeyError as e:
            return {"ok": False, "error": f"unknown_core_tool:{e}", "tool": name}
        except Exception as e:
            return {"ok": False, "error": str(e), "tool": name}

    if name in ("execute_code", "ability.code_execution"):
        code = str(arguments.get("code") or arguments.get("input") or "")
        if not code:
            code = "print(2+2)"
        # Prefer core CodeExecutionTool when available
        reg = _core_tool_registry()
        if reg:
            try:
                from core.tools.permissions import Permissions

                ctx = {"allowed_permissions": ["CODE_EXEC"]}
                if hasattr(Permissions, "CODE_EXEC"):
                    ctx["allowed_permissions"].append(Permissions.CODE_EXEC)
                result = reg.execute_tool("code_exec", {"code": code}, context=ctx)
                return {"ok": True, "result": result, "source": "core.tools.code_exec"}
            except Exception as e:
                pass  # fall through to sandbox
        try:
            from core.security.python_sandbox import PythonSandbox

            sb = PythonSandbox(
                timeout_seconds=5,
                allowed_imports=(
                    "math",
                    "json",
                    "re",
                    "datetime",
                    "collections",
                    "itertools",
                ),
            )
            return {"ok": True, "result": sb.run(code)}
        except Exception as e:
            # Local fallback when core.security is not importable as top-level `core`
            try:
                import io
                from contextlib import redirect_stdout

                buf = io.StringIO()
                loc: Dict[str, Any] = {}
                with redirect_stdout(buf):
                    exec(code, {"__builtins__": {"print": print, "range": range, "len": len, "str": str, "int": int, "float": float}}, loc)
                return {
                    "ok": True,
                    "result": {"stdout": buf.getvalue(), "locals": {k: repr(v) for k, v in loc.items() if not k.startswith("_")}},
                    "source": "local_exec_fallback",
                    "sandbox_error": str(e),
                }
            except Exception as e2:
                return {
                    "ok": False,
                    "error": f"sandbox_unavailable:{e}",
                    "fallback_error": str(e2),
                    "hint": "code not executed",
                }

    if name in ("web_research", "ability.web_research"):
        return _web_research(
            str(arguments.get("query") or arguments.get("input") or "RealAI local hive"),
            int(arguments.get("max_results") or 5),
        )

    if name.startswith("ability."):
        aid = name.split(".", 1)[-1]
        # Ability modules under abilities/ (UNIFY_PLAN steps 2–4)
        ability_handlers = {
            "coach": "abilities.rackup.coach",
            "professional_coach": "abilities.rackup.coach",
            "shot_of_the_day": "abilities.rackup.shot_of_the_day",
            "sotd": "abilities.rackup.shot_of_the_day",
            "rating_update": "abilities.rackup.rating_update",
            "skill_update": "abilities.rackup.rating_update",
            "post_match_rating": "abilities.rackup.rating_update",
            "tournament": "abilities.rackup.tournament",
            "tournament_insights": "abilities.rackup.tournament",
            "ledger_audit": "abilities.rackup.ledger_audit",
            "money_audit": "abilities.rackup.ledger_audit",
            "matchmaking": "abilities.rackup.matchmaking",
            "matchmaking_advice": "abilities.rackup.matchmaking",
                        "hall_context": "abilities.rackup.hall_context",
                        "league_validate": "abilities.rackup.league_validate",
                        "moderation": "abilities.rackup.moderation",
                        "money_anomaly": "abilities.rackup.money_anomaly",
                        "payout_sanity": "abilities.rackup.payout_sanity",
                        "pyramid_rules": "abilities.rackup.pyramid_rules",
                        "rating_convert": "abilities.rackup.rating_convert",
                        "rating_intel": "abilities.rackup.rating_intel",
                        "sotd_contribute": "abilities.rackup.sotd_contribute",
                        "video_analysis": "abilities.rackup.video_analysis",
                        "desktop_lambda_chat": "abilities.desktop_lambda_chat",
                        "desktop_lambda_image": "abilities.desktop_lambda_image",
                        "desktop_lambda_video": "abilities.desktop_lambda_video",
                        "desktop_lambda_advanced": "abilities.desktop_lambda_advanced",
                        "overmind_runner": "abilities.overmind_runner",
                        "code_engineer_agent": "abilities.code_engineer_agent",
                        "code_engineer_cli": "abilities.code_engineer_cli",
                        "quarantine_reconstruct": "abilities.quarantine_reconstruct",
                        "nest_orchestrators": "abilities.nest_orchestrators",
            "game_world": "abilities.game_world",
            "atomic_fizz": "abilities.game_world",
            "organs_hive": "abilities.organs_hive",
            "organs": "abilities.organs_hive",
            "web3_integration": "abilities.web3_integration",
            "deep_promote": "abilities.deep_promote",
            "nested_gold": "abilities.deep_promote",
            "promote_deep": "abilities.deep_promote",
            "hierarchical_specialists": "abilities.hierarchical_specialists",
            "specialists": "abilities.hierarchical_specialists",
            "approval_store": "abilities.approval_store",
            "device_selector": "abilities.device_selector",
            "memory_learning": "abilities.memory_learning",
            "knowledge_synthesis": "abilities.knowledge_synthesis",
            "observability_self_improve": "abilities.observability_self_improve",
            "cli_surface": "abilities.cli_surface",
            "hive_orchestrator": "abilities.hive_orchestrator",
            "hive": "abilities.hive_orchestrator",
            "hive_memory": "abilities.hive_memory",
            "nest_orchestrators": "abilities.nest_orchestrators",
            "nests": "abilities.nest_orchestrators",
            "orchestration_surface": "abilities.orchestration_surface",
            "orchestration": "abilities.orchestration_surface",
            "orch_surface": "abilities.orchestration_surface",
            "plugins_surface": "abilities.plugins_surface",
            "plugins": "abilities.plugins_surface",
            "plugin_surface": "abilities.plugins_surface",
            "learn_git": "abilities.learn_git",
            "git_learn": "abilities.learn_git",
            "agents_surface": "abilities.agents_surface",
            "agents": "abilities.agents_surface",
            "agent_tools_surface": "abilities.agent_tools_surface",
            "agent_tools": "abilities.agent_tools_surface",
            "core_surface": "abilities.core_surface",
            "core": "abilities.core_surface",
            "modules_surface": "abilities.modules_surface",
            "modules": "abilities.modules_surface",
            "repo_surface": "abilities.repo_surface",
            "repo": "abilities.repo_surface",
            "audio_transcription": "abilities.audio_transcription",
            "audio_speech": "abilities.audio_speech",
            "voice_streaming": "abilities.voice_streaming",
            "image_analysis": "abilities.image_analysis",
            "image_generation": "abilities.image_generation",
            "video_generation": "abilities.video_generation",
            "hive_governance": "abilities.hive_governance",
            "hominis_enterprise": "abilities.hominis_enterprise",
            "omnibrain": "abilities.omnibrain",
            "world_brain": "abilities.world_brain",
            "world-brain": "abilities.world_brain",
            "overseer": "abilities.overseer",
            "overseer_77": "abilities.overseer",
        }
        import importlib

        module_name = ability_handlers.get(aid) or f"abilities.{aid}"
        try:
            mod = importlib.import_module(module_name)
            ctx = arguments.get("context") if isinstance(arguments.get("context"), dict) else {}
            payload = dict(arguments)
            payload.pop("input", None)
            payload.pop("context", None)
            if not hasattr(mod, "run"):
                # web3_integration exposes get_web3_tool()
                if aid == "web3_integration" and hasattr(mod, "get_web3_tool"):
                    tool = mod.get_web3_tool()
                    return {
                        "ok": True,
                        "ability": aid,
                        "tool": name,
                        "source": "abilities.web3_integration",
                        "result": {
                            "web3_tool": type(tool).__name__,
                            "note": "policy-gated Web3Tool constructed; no CLI husk used",
                        },
                    }
                return {"ok": False, "error": "no_run_entrypoint", "ability": aid, "tool": name}
            out = _invoke_ability_run(
                mod.run,
                aid=aid,
                raw_input=str(arguments.get("input") or ""),
                context={**ctx, **payload},
            )
            if isinstance(out, dict):
                out["tool"] = name
            else:
                out = {"ok": True, "ability": aid, "tool": name, "result": out}
            return out
        except ModuleNotFoundError:
            pass
        except Exception as e:
            return {"ok": False, "error": str(e), "ability": aid, "tool": name}
        try:
            from realai.ability_catalog import coverage_summary, build_catalog

            cat = build_catalog()
            entry = next(
                (a for a in (cat.get("abilities") or []) if a.get("id") == aid),
                None,
            )
            return {
                "ok": True,
                "ability": aid,
                "entry": entry,
                "coverage": (coverage_summary().get("coverage") or {}),
                "input": arguments.get("input"),
                "note": "Ability invoked via catalog; live_path handlers run through orchestrator tools when available.",
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    return {"ok": False, "error": f"registry_tool_not_implemented:{name}"}


def _web_research(query: str, max_results: int = 5) -> Dict[str, Any]:
    query = (query or "").strip()
    if not query:
        return {"ok": False, "error": "query required"}
    url = (
        "https://api.duckduckgo.com/?q="
        + urllib.request.quote(query)
        + "&format=json&no_html=1"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RealAI-clean/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        results = []
        if data.get("AbstractText"):
            results.append(
                {
                    "title": data.get("Heading") or "Abstract",
                    "snippet": data.get("AbstractText"),
                    "url": data.get("AbstractURL"),
                }
            )
        for t in (data.get("RelatedTopics") or [])[: max(0, max_results - len(results))]:
            if isinstance(t, dict) and t.get("Text"):
                results.append(
                    {
                        "title": (t.get("Text") or "")[:80],
                        "snippet": t.get("Text"),
                        "url": t.get("FirstURL"),
                    }
                )
        return {
            "ok": True,
            "query": query,
            "results": results[:max_results],
            "provider": "duckduckgo",
        }
    except Exception as e:
        return {
            "ok": False,
            "query": query,
            "error": str(e),
            "hint": "Network research unavailable offline; use workspace_grep / multi_agent instead.",
        }


# ---------------------------------------------------------------------------
# Workspace file tools (B3 piece 1): confined, capped, read-only by default.
#
# Platform notes (Security #210 MED 3):
#   POSIX: every path is walked component by component with directory fds
#     (O_DIRECTORY|O_NOFOLLOW + dir_fd); the leaf is opened with O_NOFOLLOW
#     (and O_NONBLOCK for reads) and checked with fstat (S_ISREG, st_nlink == 1)
#     before a single byte is read or written. Data is read/written through
#     that fd, so a component swapped for a symlink after the check cannot be
#     followed (no TOCTOU window).
#   Windows: dir_fd and O_NOFOLLOW do not exist. Each component is lstat'ed and
#     refused if it is a reparse point (symlink, junction, mount point:
#     FILE_ATTRIBUTE_REPARSE_POINT); after the leaf is opened, the handle's
#     final path (GetFinalPathNameByHandleW) must still be inside the root and
#     must not hit the denylist (this also defeats 8.3 short names), then fstat
#     checks S_ISREG and st_nlink == 1. Data goes through the checked handle.
#     The remaining window is a directory swapped between lstat and open; the
#     final-path check after open catches that case.
# ---------------------------------------------------------------------------
import stat as _stat
import time as _time

WS_MAX_READ_BYTES = 1_000_000      # largest file we will open for read/grep
WS_MAX_CONTENT = 64 * 1024         # bytes of content returned per read
WS_MAX_LINE = 4096                 # chars per returned line
WS_MAX_WRITE_BYTES = 256 * 1024    # bytes accepted per write
WS_MAX_LINES = 200
WS_MAX_LIST = 200
WS_MAX_GREP_FILES = 2000
WS_MAX_GREP_HITS = 40
WS_MAX_GREP_FILE_BYTES = 1_000_000
WS_MAX_GREP_TOTAL_BYTES = 20_000_000
WS_GREP_DEADLINE_S = 5.0
WS_GREP_MAX_DEPTH = 20
WS_MAX_PATTERN = 200
WS_MAX_PATH = 1024
WS_BINARY_SNIFF = 8192
WS_READ_TOOLS = ("workspace_list", "workspace_read", "workspace_grep")
WS_WRITE_TOOLS = ("workspace_write",)
_WS_SKIP_DIRS = {"node_modules", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache"}
_WS_DENY_EXACT = {".env", ".git", ".npmrc", ".pypirc", ".netrc", ".realai", ".approvals.json", ".ssh", ".aws",
                  ".docker", ".htpasswd"}
_WS_DENY_SUFFIX = (".pem", ".key", ".p12", ".pfx", ".keystore", ".kdbx", ".tfstate")
_WS_DENY_PREFIX = (".env.", "id_", "credentials")
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400
_WS_POSIX = os.name != "nt" and os.open in getattr(os, "supports_dir_fd", set()) and hasattr(os, "O_NOFOLLOW")


class WorkspacePathError(ValueError):
    """Rejected path; .code is a stable, path-free reason."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def ws_denied_name(name: str) -> bool:
    """Case-insensitive secret/credential denylist for ONE path component."""
    n = name.lower().rstrip(" .")  # Windows ignores trailing dots/spaces
    if not n:
        return False
    return (
        n in _WS_DENY_EXACT
        or n.startswith(_WS_DENY_PREFIX)
        or n.endswith(_WS_DENY_SUFFIX)
        or "secret" in n
        or (n.endswith(".json") and (n.startswith("keypair") or "wallet" in n))  # Solana keypairs / wallet files
    )


def _ws_forbidden_roots() -> List[Path]:
    out = []
    for p in (Path.home(), Path(__file__).resolve().parents[2]):
        try:
            out.append(p.resolve())
        except OSError:
            pass
    return out


def workspace_root() -> Path:
    """Confinement root: REALAI_TOOLS_WORKSPACE_ROOT only. Fail closed (no fallback).

    Refuses /, a drive root, the user's home, the product (repo) root, or any ancestor of those.
    """
    raw = os.environ.get("REALAI_TOOLS_WORKSPACE_ROOT", "").strip()
    if not raw:
        raise WorkspacePathError("workspace_unavailable")
    try:
        root = Path(raw).resolve(strict=True)
    except (OSError, RuntimeError):
        raise WorkspacePathError("workspace_unavailable") from None
    if not root.is_dir() or root.parent == root:
        raise WorkspacePathError("workspace_unavailable")
    for bad in _ws_forbidden_roots():
        if root == bad or root in bad.parents:
            raise WorkspacePathError("workspace_unavailable")
    return root


def ws_parts(rel: Any) -> List[str]:
    """Validate a caller path and split it into components (no I/O)."""
    from pathlib import PurePosixPath, PureWindowsPath

    s = "." if rel is None or rel == "" else rel
    if not isinstance(s, str):
        raise WorkspacePathError("bad_path_type")
    if len(s) > WS_MAX_PATH or "\x00" in s:
        raise WorkspacePathError("bad_path")
    if s.startswith(("\\\\", "//")):
        raise WorkspacePathError("unc_path_not_allowed")
    w = PureWindowsPath(s)
    if s.startswith(("/", "\\")) or w.drive or w.is_absolute() or PurePosixPath(s).is_absolute() or ":" in s:
        raise WorkspacePathError("absolute_path_not_allowed")
    parts = [x for x in re.split(r"[\\/]+", s) if x not in ("", ".")]
    if any(x == ".." for x in parts):
        raise WorkspacePathError("path_traversal_not_allowed")
    if os.name == "nt" and any(x.rstrip(" .") in ("", "..") for x in parts):
        raise WorkspacePathError("bad_path")  # "... " / ".. " collapse to dots on Windows
    for x in parts:
        if ws_denied_name(x):
            raise WorkspacePathError("denied_path")
    return parts


def _ws_err(e: OSError, default: str = "io_error") -> WorkspacePathError:
    import errno

    if e.errno == errno.ELOOP:
        return WorkspacePathError("symlink_not_allowed")
    if e.errno == errno.ENOENT:
        return WorkspacePathError("not_found")
    if e.errno in (errno.ENOTDIR,):
        return WorkspacePathError("not_a_directory")
    if e.errno in (errno.EISDIR,):
        return WorkspacePathError("not_a_file")
    return WorkspacePathError(default)


def _ws_guard(root: Path, parts: List[str]) -> str:
    """Normalized absolute path for root/parts, guaranteed under root (also the sanitizer CodeQL recognizes)."""
    root_s = os.path.normpath(str(root))
    full = os.path.normpath(os.path.join(root_s, *parts))
    if full != root_s and not full.startswith(root_s.rstrip("\\/") + os.sep):
        raise WorkspacePathError("outside_workspace")
    return full


# ---- POSIX fd walk -------------------------------------------------------------
def _px_open_dir(root: Path, parts: List[str], *, create: bool = False) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    dfd = os.open(_ws_guard(root, []), os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0))
    try:
        for i in range(len(parts)):
            comp = os.path.basename(_ws_guard(root, parts[: i + 1]))
            try:
                nfd = os.open(comp, flags, dir_fd=dfd)
            except FileNotFoundError:
                if not create:
                    raise WorkspacePathError("not_found") from None
                os.mkdir(comp, 0o755, dir_fd=dfd)
                nfd = os.open(comp, flags, dir_fd=dfd)
            except OSError as e:
                try:
                    st = os.stat(comp, dir_fd=dfd, follow_symlinks=False)
                    code = "symlink_not_allowed" if _stat.S_ISLNK(st.st_mode) else "not_a_directory"
                except OSError:
                    code = _ws_err(e).code
                raise WorkspacePathError(code) from None
            os.close(dfd)
            dfd = nfd
        return dfd
    except BaseException:
        os.close(dfd)
        raise


def _px_open_leaf(dfd: int, root: Path, parts: List[str], flags: int, mode: int = 0o644) -> int:
    name = os.path.basename(_ws_guard(root, parts))
    try:
        return os.open(name, flags | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0), mode, dir_fd=dfd)
    except OSError as e:
        try:
            st = os.stat(name, dir_fd=dfd, follow_symlinks=False)
            if _stat.S_ISLNK(st.st_mode):
                raise WorkspacePathError("symlink_not_allowed") from None
        except FileNotFoundError:
            pass
        except WorkspacePathError:
            raise
        except OSError:
            pass
        raise _ws_err(e) from None


# ---- Windows checks ------------------------------------------------------------
def _nt_is_reparse(p: Path) -> bool:
    st = os.lstat(str(p))
    return bool(getattr(st, "st_file_attributes", 0) & _FILE_ATTRIBUTE_REPARSE_POINT) or _stat.S_ISLNK(st.st_mode)


def _nt_walk(root: Path, parts: List[str], *, create_parents: bool = False) -> Path:
    cur = Path(_ws_guard(root, []))
    for i in range(len(parts)):
        cur = Path(_ws_guard(root, parts[: i + 1]))
        try:
            if _nt_is_reparse(cur):
                raise WorkspacePathError("symlink_not_allowed")
        except FileNotFoundError:
            if create_parents and i < len(parts) - 1:
                os.mkdir(str(cur))
                continue
            if i == len(parts) - 1:
                return cur
            raise WorkspacePathError("not_found") from None
    return cur


def _nt_final_path(fd: int) -> Optional[str]:
    try:
        import ctypes
        import msvcrt
        from ctypes import wintypes

        h = msvcrt.get_osfhandle(fd)
        fn = ctypes.windll.kernel32.GetFinalPathNameByHandleW
        fn.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
        fn.restype = wintypes.DWORD
        buf = ctypes.create_unicode_buffer(32768)
        n = fn(h, buf, 32768, 0)
        if not n or n >= 32768:
            return None
        s = buf.value
        if s.startswith("\\\\?\\UNC\\"):
            s = "\\\\" + s[8:]
        elif s.startswith("\\\\?\\"):
            s = s[4:]
        return s
    except Exception:
        return None


def _nt_check_final(root: Path, fd: int) -> None:
    final = _nt_final_path(fd)
    if final is None:
        raise WorkspacePathError("io_error")
    fp = Path(final)
    try:
        rel = fp.relative_to(root)
    except ValueError:
        try:
            rel = Path(os.path.normcase(final)).relative_to(Path(os.path.normcase(str(root))))
        except ValueError:
            raise WorkspacePathError("outside_workspace") from None
    if any(ws_denied_name(x) for x in rel.parts):
        raise WorkspacePathError("denied_path")


# ---- secure open (both platforms) ----------------------------------------------
def _ws_check_regular(fd: int) -> os.stat_result:
    st = os.fstat(fd)
    if not _stat.S_ISREG(st.st_mode):
        raise WorkspacePathError("not_a_file")
    if st.st_nlink > 1:
        raise WorkspacePathError("hardlink_not_allowed")
    return st


def ws_open_read(root: Path, parts: List[str]) -> int:
    """Open a regular, single-link file under root for reading; returns an fd."""
    if not parts:
        raise WorkspacePathError("not_a_file")
    if _WS_POSIX:
        dfd = _px_open_dir(root, parts[:-1])
        try:
            fd = _px_open_leaf(dfd, root, parts, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
        finally:
            os.close(dfd)
    else:
        p = _nt_walk(root, parts)
        if p.is_dir():
            raise WorkspacePathError("not_a_file")
        try:
            fd = os.open(str(p), os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0))
        except OSError as e:
            raise _ws_err(e) from None
        try:
            _nt_check_final(root, fd)
        except BaseException:
            os.close(fd)
            raise
    try:
        _ws_check_regular(fd)
    except BaseException:
        os.close(fd)
        raise
    return fd


def _ws_read_fd(fd: int, limit: int) -> bytes:
    chunks, total = [], 0
    while total <= limit:
        b = os.read(fd, min(65536, limit + 1 - total))
        if not b:
            break
        chunks.append(b)
        total += len(b)
    return b"".join(chunks)


def ws_read_bytes(root: Path, parts: List[str], limit: int) -> bytes:
    fd = ws_open_read(root, parts)
    try:
        if os.fstat(fd).st_size > limit:
            raise WorkspacePathError("file_too_large")
        data = _ws_read_fd(fd, limit)
        if len(data) > limit:
            raise WorkspacePathError("file_too_large")
        return data
    finally:
        os.close(fd)


def _ws_is_binary(data: bytes) -> bool:
    return b"\x00" in data[:WS_BINARY_SNIFF]


def ws_resolve(root: Path, rel: Any) -> Path:
    """Back-compat: validate a caller path and return root/parts (refuses links on the way)."""
    parts = ws_parts(rel)
    if _WS_POSIX:
        if parts:
            dfd = _px_open_dir(root, parts[:-1])
            try:
                st = os.stat(os.path.basename(_ws_guard(root, parts)), dir_fd=dfd, follow_symlinks=False)
                if _stat.S_ISLNK(st.st_mode):
                    raise WorkspacePathError("symlink_not_allowed")
            except FileNotFoundError:
                pass
            finally:
                os.close(dfd)
        return Path(_ws_guard(root, parts))
    return _nt_walk(root, parts) if parts else root


def _ws_int(v: Any, default: int, lo: int, hi: int) -> int:
    if v is None or v == "":
        return default
    if isinstance(v, bool):
        raise WorkspacePathError("bad_number")
    try:
        n = int(v)
    except (TypeError, ValueError):
        raise WorkspacePathError("bad_number") from None
    return max(lo, min(hi, n))


def _ws_write_allowed() -> bool:
    allow = {x.strip() for x in os.environ.get("REALAI_TOOLS_ALLOW", "").split(",") if x.strip()}
    return "workspace_write" in allow


def _ws_entry_kind(st: os.stat_result) -> str:
    if _stat.S_ISLNK(st.st_mode) or getattr(st, "st_file_attributes", 0) & _FILE_ATTRIBUTE_REPARSE_POINT:
        return "link"
    if _stat.S_ISDIR(st.st_mode):
        return "dir"
    if _stat.S_ISREG(st.st_mode):
        return "file"
    return "other"


def _ws_scandir(root: Path, parts: List[str]):
    """Yield (name, lstat) for a directory under root, opened safely."""
    if _WS_POSIX:
        dfd = _px_open_dir(root, parts)
        try:
            with os.scandir(dfd) as it:
                ents = [(e.name, e.stat(follow_symlinks=False)) for e in it]
        finally:
            os.close(dfd)
        return ents
    d = _nt_walk(root, parts) if parts else Path(_ws_guard(root, []))
    try:
        if not _stat.S_ISDIR(os.lstat(str(d)).st_mode):
            raise WorkspacePathError("not_a_directory")
        with os.scandir(str(d)) as it:
            return [(e.name, e.stat(follow_symlinks=False)) for e in it]
    except FileNotFoundError:
        raise WorkspacePathError("not_found") from None


def _ws_list(root: Path, a: Dict[str, Any]) -> Dict[str, Any]:
    parts = ws_parts(a.get("path"))
    rel = "/".join(parts) or "."
    try:
        ents = _ws_scandir(root, parts)
    except WorkspacePathError as e:
        if e.code != "not_a_directory" or not parts:
            raise
        fd = ws_open_read(root, parts)
        try:
            return {"ok": True, "path": rel, "type": "file", "size": os.fstat(fd).st_size}
        finally:
            os.close(fd)
    ents = [(n, st) for n, st in ents if n not in _WS_SKIP_DIRS and not ws_denied_name(n)]
    ents.sort(key=lambda x: (_ws_entry_kind(x[1]) != "dir", x[0].lower()))
    entries = [{"name": n, "type": _ws_entry_kind(st)} for n, st in ents[:WS_MAX_LIST]]
    return {"ok": True, "path": rel, "entries": entries, "truncated": len(ents) > WS_MAX_LIST}


def _ws_read(root: Path, a: Dict[str, Any]) -> Dict[str, Any]:
    parts = ws_parts(a.get("path"))
    start = _ws_int(a.get("start"), 1, 1, 10_000_000)
    limit = _ws_int(a.get("limit"), 80, 1, WS_MAX_LINES)
    data = ws_read_bytes(root, parts, WS_MAX_READ_BYTES)
    if _ws_is_binary(data):
        return {"ok": False, "error": "binary_not_allowed"}
    lines = data.decode("utf-8", errors="replace").splitlines()
    chunk, used, truncated = [], 0, False
    for line in lines[start - 1 : start - 1 + limit]:
        if len(line) > WS_MAX_LINE:
            line, truncated = line[:WS_MAX_LINE], True
        cost = len(line.encode("utf-8")) + 1
        if used + cost > WS_MAX_CONTENT:
            truncated = True
            break
        chunk.append(line)
        used += cost
    return {"ok": True, "path": "/".join(parts), "start": start, "lines": chunk,
            "content": "\n".join(chunk), "total_lines": len(lines), "truncated": truncated}


def _ws_grep(root: Path, a: Dict[str, Any]) -> Dict[str, Any]:
    import fnmatch

    pattern = a.get("pattern")
    if not isinstance(pattern, str) or not pattern or len(pattern) > WS_MAX_PATTERN:
        return {"ok": False, "error": "bad_pattern"}
    glob = str(a.get("glob") or "*")[:100]
    base = ws_parts(a.get("path"))
    deadline = _time.monotonic() + WS_GREP_DEADLINE_S
    hits: List[Dict[str, Any]] = []
    scanned = 0
    budget = WS_MAX_GREP_TOTAL_BYTES
    stack: List[List[str]] = [base]
    while stack:
        if _time.monotonic() > deadline:
            return {"ok": True, "hits": hits, "truncated": True, "reason": "deadline"}
        parts = stack.pop()
        try:
            ents = _ws_scandir(root, parts)
        except WorkspacePathError:
            if parts is base:
                raise
            continue
        except OSError:
            continue
        subdirs = []
        for name, st in sorted(ents, key=lambda x: x[0]):
            if name in _WS_SKIP_DIRS or ws_denied_name(name):
                continue
            kind = _ws_entry_kind(st)
            if kind == "dir":
                if len(parts) - len(base) < WS_GREP_MAX_DEPTH:
                    subdirs.append(parts + [name])
                continue
            if kind != "file" or st.st_nlink > 1 or not fnmatch.fnmatch(name, glob):
                continue
            if st.st_size > WS_MAX_GREP_FILE_BYTES:
                continue
            scanned += 1
            if scanned > WS_MAX_GREP_FILES or budget <= 0 or _time.monotonic() > deadline:
                return {"ok": True, "hits": hits, "truncated": True}
            try:
                data = ws_read_bytes(root, parts + [name], WS_MAX_GREP_FILE_BYTES)
            except (WorkspacePathError, OSError):
                continue
            budget -= len(data)
            if _ws_is_binary(data):
                continue
            rel = "/".join(parts + [name])
            for i, line in enumerate(data.decode("utf-8", errors="ignore").splitlines(), 1):
                if pattern in line:  # literal match: no regex, no ReDoS
                    hits.append({"path": rel, "line": i, "text": line[:300]})
                    if len(hits) >= WS_MAX_GREP_HITS:
                        return {"ok": True, "hits": hits, "truncated": True}
        stack.extend(reversed(subdirs))
    return {"ok": True, "hits": hits, "truncated": False}


def ws_write_bytes(root: Path, parts: List[str], data: bytes, *, append: bool = False) -> None:
    """Write through a checked fd: no symlink/junction hop, regular file, st_nlink == 1."""
    if not parts:
        raise WorkspacePathError("not_a_file")
    flags = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if append else 0)
    if _WS_POSIX:
        dfd = _px_open_dir(root, parts[:-1], create=True)
        try:
            fd = _px_open_leaf(dfd, root, parts, flags | getattr(os, "O_NONBLOCK", 0))
        finally:
            os.close(dfd)
    else:
        p = _nt_walk(root, parts, create_parents=True)
        try:
            fd = os.open(str(p), flags | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0), 0o644)
        except OSError as e:
            raise _ws_err(e) from None
        try:
            _nt_check_final(root, fd)
        except BaseException:
            os.close(fd)
            raise
    try:
        st = _ws_check_regular(fd)
        if append and st.st_size + len(data) > WS_MAX_READ_BYTES:
            raise WorkspacePathError("file_too_large")
        if not append:
            os.ftruncate(fd, 0)
        view = memoryview(data)
        while view:
            n = os.write(fd, view)
            view = view[n:]
    finally:
        os.close(fd)


def _ws_write(root: Path, a: Dict[str, Any]) -> Dict[str, Any]:
    if not _ws_write_allowed():
        return {"ok": False, "error": "write_not_allowed",
                "message": "workspace_write is off; add it to REALAI_TOOLS_ALLOW to enable."}
    content = a.get("content", "")
    if not isinstance(content, str):
        return {"ok": False, "error": "bad_content"}
    data = content.encode("utf-8")
    if len(data) > WS_MAX_WRITE_BYTES:
        return {"ok": False, "error": "content_too_large", "max_bytes": WS_MAX_WRITE_BYTES}
    if "\x00" in content:
        return {"ok": False, "error": "binary_not_allowed"}
    mode = str(a.get("mode") or "overwrite")
    if mode not in ("overwrite", "append"):
        return {"ok": False, "error": "bad_mode"}
    if not a.get("path"):
        return {"ok": False, "error": "bad_path"}
    parts = ws_parts(a.get("path"))
    ws_write_bytes(root, parts, data, append=(mode == "append"))
    return {"ok": True, "path": "/".join(parts), "bytes": len(data), "mode": mode}


def workspace_tool(
    name: str, arguments: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Confined file tools. Read-only by default; workspace_write needs REALAI_TOOLS_ALLOW.

    Auth, allowlist, rate limit and audit come from /v1/tools/execute (tool_auth, #195).
    Errors are stable codes and never echo server paths.
    """
    a = arguments if isinstance(arguments, dict) else {}
    handlers = {"workspace_list": _ws_list, "workspace_read": _ws_read,
                "workspace_grep": _ws_grep, "workspace_write": _ws_write}
    fn = handlers.get(name)
    if fn is None:
        return {"ok": False, "error": f"unknown_workspace_tool:{name}"}
    try:
        root = workspace_root()
    except WorkspacePathError as e:
        return {"ok": False, "error": e.code}
    try:
        return fn(root, a)
    except WorkspacePathError as e:
        return {"ok": False, "error": e.code}
    except OSError:
        return {"ok": False, "error": "io_error"}
