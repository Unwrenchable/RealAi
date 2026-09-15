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
                "payload": {"type": "object"},
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
        "NOT Apache Hive, NOT Hadoop, NOT Hive CLI, NOT Hiveserver2. "
        "Never emit Apache/Hadoop install or SQL-warehouse steps unless the user "
        "explicitly wrote 'Apache Hive' or 'Hadoop'. "
        "Produce a short numbered plan (3-5 steps) for the RealAI product/workspace task. "
        "Prefer concrete local checks: orchestrator :8001 health, Vulkan :8080, "
        "/v1/hive, /v1/agents, console/abilities — not generic 'sync all git repos'."
    ),
    "worker": (
        "You are the RealAI HIVE WORKER. You will be given REAL probe JSON from the "
        "local stack (already executed). Summarize only those facts in 6-10 bullets: "
        "what is up/down, agent counts, risks, and the next 2 concrete console actions. "
        "Do not invent stdout. Do not ask for $ /run /py commands — probes already ran. "
        "Forbidden: Apache Hive/Hadoop unless explicitly requested."
    ),
    "critic": (
        "You are the RealAI HIVE CRITIC. Review planner + REAL worker probe summary. "
        "If either stage drifted into Apache Hive/Hadoop, reject that drift. "
        "Verdict: pass/fail on whether the plan matches the live stack facts, "
        "plus top 3 gaps focused on RealAI multi-agent health."
    ),
}

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


BRIDGE_MULTI_REVISION = "2026-09-08-pwc-vscode-patches-v3"

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
        "- Prefer the deterministic auditor pattern: name file, Change, Why, LANDED|PROPOSED.\n"
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
    probe_report = _format_worker_probe_report(probes)
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
        },
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
        path = str(arguments.get("path") or arguments.get("file") or "")
        old = arguments.get("old_string") or arguments.get("old")
        new = arguments.get("new_string") or arguments.get("new") or arguments.get("content")
        if old is not None and new is not None and path:
            try:
                from realai.cli import craft

                cur = craft.tool_read(path, start=1, limit=50000)
                text = ""
                if isinstance(cur, dict):
                    text = str(cur.get("content") or cur.get("text") or "")
                if str(old) not in text:
                    return {
                        "ok": False,
                        "error": "old_string_not_found",
                        "path": path,
                        "tool": name,
                    }
                updated = text.replace(str(old), str(new), 1)
                return craft.tool_write(path, content=updated, mode="overwrite")
            except Exception as e:
                return {"ok": False, "error": str(e), "tool": name}
        return workspace_tool(
            "workspace_write",
            {
                "path": path,
                "content": new if new is not None else arguments.get("content"),
            },
        )
    if name == "workspace_grep" or name == "grep":
        return workspace_tool("workspace_grep", arguments)

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


def workspace_tool(
    name: str, arguments: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """File tools rooted at REALAI_WORKSPACE (portable projects)."""
    arguments = arguments or {}
    try:
        from realai.cli import craft

        if name == "workspace_list":
            return craft.tool_list(str(arguments.get("path") or "."))
        if name == "workspace_read":
            return craft.tool_read(
                str(arguments.get("path") or ""),
                start=int(arguments.get("start") or 1),
                limit=int(arguments.get("limit") or 80),
            )
        if name == "workspace_grep":
            return craft.tool_grep(
                str(arguments.get("pattern") or ""),
                path=str(arguments.get("path") or "."),
                glob=str(arguments.get("glob") or "*"),
            )
        if name == "workspace_write":
            return craft.tool_write(
                str(arguments.get("path") or ""),
                content=str(arguments.get("content") or ""),
                mode=str(arguments.get("mode") or "overwrite"),
            )
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": False, "error": f"unknown_workspace_tool:{name}"}