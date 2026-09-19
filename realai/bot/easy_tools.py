"""Easy RealAI tool runner — short slash + NL, live catalog, compact replies.

Builds aliases from the live tools catalog + ability catalog each call so
new abilities/plugins show up in ``/tools`` without a static list rewrite.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

# Stable short aliases → canonical tool name (always available).
# Live catalog names are also registered as themselves and with /t <name>.
STATIC_ALIASES: Dict[str, str] = {
    "heal": "self_heal_status",
    "self-heal": "self_heal_status",
    "self_heal": "self_heal_status",
    "heal-status": "self_heal_status",
    "assemble": "self_heal_assemble",
    "promote": "self_heal_promote_dry",
    "promote-dry": "self_heal_promote_dry",
    "agents": "list_agents",
    "agent": "list_agents",
    "recovery": "recovery_status",
    "lora": "list_lora_adapters",
    "adapters": "list_lora_adapters",
    "llama": "local_llama_health",
    "vulkan": "local_llama_health",
    "health-llama": "local_llama_health",
    "training": "training_status",
    "coverage": "ability_coverage",
    "abilities": "ability_coverage",
    "multi": "multi_agent_run",
    "craft": "craft_run",
    "craft-chat": "craft_chat",
    "hive": "hive_status",
    "hive-run": "hive_run",
    "orch": "orchestration_surface",
    "orchestration": "orchestration_surface",
    "plugins": "plugins_surface",
    "plugin": "plugins_surface",
    "agents-surface": "agents_surface",
    "agent-tools": "agent_tools_surface",
    "agent_tools": "agent_tools_surface",
    "core": "core_surface",
    "modules": "modules_surface",
    "module": "modules_surface",
    "repo": "repo_surface",
    "where": "repo_surface",
    "organs": "organs_task",
    "omnibrain": "omnibrain",
    "brain": "omnibrain",
    "world": "world_brain",
    "world-brain": "world_brain",
    "overseer": "overseer",
    # Promote nest / hierarchy / engineer surfaces that live under realai/abilities
    "nests": "ability.nest_orchestrators",
    "nest": "ability.nest_orchestrators",
    "nest-orch": "ability.nest_orchestrators",
    "hierarchical": "ability.hierarchical_specialists",
    "specialists": "ability.hierarchical_specialists",
    "hierarchy": "ability.hierarchical_specialists",
    "code-engineer": "ability.code_engineer_cli",
    "engineer": "ability.code_engineer_cli",
    "ce-cli": "ability.code_engineer_cli",
    "ce-agent": "ability.code_engineer_agent",
    "hominis": "ability.hominis_enterprise",
    "governance": "ability.hive_governance",
    "quarantine": "ability.quarantine_reconstruct",
    "cli": "ability.cli_surface",
    "deep-promote": "ability.deep_promote",
    "rackup": "rackup_invoke",
    "aura": "aura_memory",
    "device": "device_selector",
    "extend": "self_extend",
    "repair": "self_repair",
    "scan": "system_scan",
    "ws-list": "workspace_list",
    "ws-read": "workspace_read",
    "ws-grep": "workspace_grep",
    "code": "execute_code",
    "exec-code": "execute_code",
    "research": "web_research",
    "web": "web_research",
    "search": "web_research",
    "image": "ability.image_generation",
    "draw": "ability.image_generation",
    "imagine": "ability.image_generation",
    "picture": "ability.image_generation",
    "video": "ability.video_generation",
    "vision": "ability.image_analysis",
    "see": "ability.image_analysis",
    "remember": "aura_memory",
    "recall": "aura_memory",
    "memory": "ability.hive_memory",
    "read": "read_file",
    "ls": "list_dir",
    "grep-ws": "workspace_grep",
    "shell-tool": "run_terminal_command",
    "at-status": "agent_tools_status",
    "at-agents": "agent_tools_list_agents",
    "at-profiles": "agent_tools_list_profiles",
    "at-tools": "agent_tools_list_tools",
    "at-invoke": "agent_tools_invoke",
    # RealAI Voice provider (local TTS / ASR)
    "voice": "voice_health",
    "voice-health": "voice_health",
    "voice-speak": "voice_speak",
    "speak": "voice_speak",
    "tts": "voice_speak",
    "voice-inventory": "voice_inventory",
    "voices": "voice_inventory",
    "voice-listen": "voice_listen",
    "listen": "voice_listen",
}


def _live_tool_names(run_tool: Optional[Callable[..., Any]] = None) -> List[str]:
    names: List[str] = []
    try:
        from realai.v3_runtime_bridge import tools_catalog

        for t in tools_catalog() or []:
            n = ((t.get("function") or {}).get("name") or "").strip()
            if n:
                names.append(n)
    except Exception:
        pass
    try:
        from realai.ability_catalog import build_catalog

        cat = build_catalog() or {}
        for a in cat.get("abilities") or []:
            aid = str(a.get("id") or "").strip()
            if not aid:
                continue
            if not aid.startswith("ability."):
                aid = "ability." + aid
            names.append(aid)
    except Exception:
        pass
    # de-dupe preserve order
    seen = set()
    out: List[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def build_alias_map(run_tool: Optional[Callable[..., Any]] = None) -> Dict[str, str]:
    """Map slash/token → canonical tool name. Rebuilt from live catalogs."""
    amap = dict(STATIC_ALIASES)
    for name in _live_tool_names(run_tool):
        amap[name.lower()] = name
        amap[name.lower().replace("_", "-")] = name
        if name.startswith("ability."):
            short = name[len("ability.") :]
            amap[short.lower()] = name
            amap[("ability." + short).lower()] = name
        if name.startswith("core."):
            amap[name.lower()] = name
    return amap


def list_easy_commands(limit: int = 120) -> Dict[str, Any]:
    """Catalog for ``/tools`` — short aliases + live tools (visibility updates live)."""
    amap = build_alias_map()
    live = _live_tool_names()
    # Prefer short aliases first
    shorts = sorted({k: v for k, v in STATIC_ALIASES.items()}.items(), key=lambda kv: kv[0])
    rows = [{"slash": f"/{k}", "tool": v} for k, v in shorts]
    for name in live[: max(0, limit - len(rows))]:
        rows.append({"slash": f"/tool {name}", "tool": name})
    return {
        "ok": True,
        "count": len(live),
        "alias_count": len(STATIC_ALIASES),
        "hint": "Run: /tool <name> [args…] · /t <name> · /hive · /lora · /heal · /coverage · /py code · $ cmd",
        "examples": [
            "/tools",
            "/hive",
            "/heal",
            "/lora",
            "/coverage",
            "/agents",
            "/tool local_llama_health",
            "/tool multi_agent_run summarize repo layout",
            "/ability cli_surface",
            "/t ability.memory_learning",
            "$ whoami",
        ],
        "commands": rows[:limit],
        "live_tools_sample": live[:40],
    }


def _parse_args_blob(rest: str) -> Dict[str, Any]:
    rest = (rest or "").strip()
    if not rest:
        return {}
    if rest.startswith("{"):
        try:
            obj = json.loads(rest)
            return obj if isinstance(obj, dict) else {"input": rest}
        except Exception:
            return {"input": rest, "task": rest, "goal": rest, "prompt": rest}
    # key=value pairs
    if re.search(r"^\w+=", rest):
        out: Dict[str, Any] = {}
        for part in re.findall(r"(\w+)=(\"[^\"]*\"|'[^']*'|\S+)", rest):
            k, v = part
            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]
            out[k] = v
        if out:
            return out
    return {"input": rest, "task": rest, "goal": rest, "prompt": rest, "query": rest, "text": rest, "command": rest}


def _default_args_for(tool: str, rest: str) -> Dict[str, Any]:
    args = _parse_args_blob(rest)
    t = tool.lower()
    if t in ("multi_agent_run", "hive_run") and rest and "task" not in args:
        args["task"] = rest
        args.setdefault("action", "cycle" if t == "hive_run" else "pipeline")
    if t == "craft_run":
        if rest and "action" not in args:
            parts = rest.split(None, 1)
            args["action"] = parts[0]
            if len(parts) > 1:
                args["goal"] = parts[1]
                args["input"] = parts[1]
        args.setdefault("action", "doctor")
    if t == "craft_chat" and rest:
        args.setdefault("prompt", rest)
    if t == "hive_status":
        args.setdefault("action", rest or "status")
    if t == "organs_task" and rest:
        args.setdefault("goal", rest)
    if t == "web_research" and rest:
        args.setdefault("query", rest)
    if t == "execute_code" and rest:
        args.setdefault("code", rest)
    if t == "read_file" and rest:
        args.setdefault("path", rest.split()[0])
    if t == "list_dir":
        args.setdefault("path", rest or ".")
    if t == "run_terminal_command" and rest:
        args.setdefault("command", rest)
    if t == "voice_speak" and rest:
        args.setdefault("text", rest)
        args.setdefault("input", rest)
    if t == "aura_memory":
        args.setdefault("action", "recall" if rest else "recall")
        if rest:
            args.setdefault("query", rest)
    if t.startswith("ability.") and rest:
        args.setdefault("input", rest)
        args.setdefault("action", "run")
    if t in ("agents_surface", "agent_tools_surface", "plugins_surface", "core_surface", "modules_surface", "orchestration_surface", "repo_surface"):
        if rest:
            parts = rest.split(None, 1)
            head = parts[0].lower()
            if head in ("list", "status", "run", "invoke", "cycle", "where", "map"):
                args["action"] = "where" if head == "map" else head
                if len(parts) > 1:
                    args["input"] = parts[1]
                    if t == "repo_surface" and args["action"] == "where":
                        args["name"] = parts[1]
                    if t == "agents_surface":
                        args["agent"] = parts[1].split()[0]
                    if t == "orchestration_surface":
                        args["orch"] = parts[1].split()[0]
            else:
                args.setdefault("action", "run" if t != "repo_surface" else "where")
                args.setdefault("input", rest)
                if t == "repo_surface":
                    args.setdefault("name", rest)
                if t == "agents_surface":
                    args.setdefault("agent", parts[0])
        else:
            args.setdefault("action", "list")
    if t == "list_lora_adapters":
        args.setdefault("limit", 30)
    return args


def parse_easy_tool(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Return (tool_name, args) if this message is an easy-tool invoke."""
    raw = (text or "").strip()
    if not raw:
        return None
    amap = build_alias_map()

    # /tools | /tool-list | /commands
    if re.match(r"^/(tools|tool-list|commands|help-tools)(?:\s|$)", raw, flags=re.I):
        return ("__list__", {})

    # /tool name …  /t name …
    m = re.match(r"^/(?:tool|t)\s+([A-Za-z0-9_.\-]+)(?:\s+([\s\S]+))?$", raw, flags=re.I)
    if m:
        key = m.group(1).strip()
        rest = (m.group(2) or "").strip()
        tool = amap.get(key.lower()) or amap.get(key.lower().replace("-", "_")) or key
        if not tool.startswith("ability.") and key.lower().startswith("ability."):
            tool = key
        return (tool, _default_args_for(tool, rest))

    # /alias rest  (static + live names as slash verbs)
    m = re.match(r"^/([A-Za-z0-9_.\-]+)(?:\s+([\s\S]*))?$", raw)
    if m:
        verb = m.group(1).strip()
        rest = (m.group(2) or "").strip()
        # leave live_exec / existing operator verbs alone if not in alias map
        # but include heal, lora, coverage, etc.
        tool = amap.get(verb.lower()) or amap.get(verb.lower().replace("-", "_"))
        # Don't steal /run /py /script /exec — live_exec owns those.
        # Don't steal Craft file ops — operator dispatch → cli.craft TOOLS.
        if verb.lower() in (
            "run",
            "py",
            "python",
            "script",
            "exec",
            "chat",
            "write",
            "read",
            "list",
            "ls",
            "grep",
            "git",
            "pwd",
            "here",
            "cat",
            "ws",
            "workspace",
        ):
            return None
        if tool:
            return (tool, _default_args_for(tool, rest))
        # /ability.foo already handled via amap; bare ability ids:
        if verb.lower().startswith("ability."):
            return (verb, _default_args_for(verb, rest))

    # Natural language: "run tool X", "show lora", "self heal status"
    low = raw.lower().strip()
    if re.match(r"^self[-\s]?heal(?:\s+status)?\s*$", low):
        return ("self_heal_status", {})
    if re.match(r"^hive(?:\s+status)?\s*$", low):
        return ("hive_status", {"action": "status"})

    nl_patterns = [
        (r"^(?:run|use|call|invoke)\s+tool\s+([a-z0-9_.\-]+)\s*(.*)$", 1, 2),
        (r"^(?:run|use|call|invoke)\s+([a-z0-9_.\-]+)\s*(.*)$", 1, 2),
        (
            r"^(?:show|get|check)\s+(lora|adapters|coverage|abilities|agents|recovery|training|hive|heal)\s*$",
            1,
            None,
        ),
        (r"^list\s+(agents|lora|adapters|tools|abilities)\s*$", 1, None),
    ]
    for pat, g_tool, g_rest in nl_patterns:
        m = re.match(pat, low, flags=re.I | re.S)
        if not m:
            continue
        key = m.group(g_tool).strip() if g_tool else ""
        rest = ""
        if g_rest and m.lastindex and g_rest <= m.lastindex:
            rest = (m.group(g_rest) or "").strip()
        key = {
            "adapters": "lora",
            "abilities": "coverage",
            "tools": "__list__",
            "heal": "heal",
        }.get(key, key)
        if key == "__list__":
            return ("__list__", {})
        # Skip generic verbs that are not tools (run hive is handled elsewhere)
        if key in ("craft", "hive") and not rest and "invoke" not in pat:
            if key == "hive":
                return ("hive_status", {"action": "status"})
        tool = amap.get(key) or amap.get(key.replace("-", "_"))
        if tool:
            if tool == "multi_agent_run" and not rest:
                continue
            return (tool, _default_args_for(tool, rest))
    return None


def _clip(s: str, n: int = 240) -> str:
    s = str(s or "").replace("\r\n", "\n").strip()
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def format_easy_result(tool: str, result: Any) -> str:
    """Compact human reply — no JSON walls."""
    if tool == "__list__":
        data = result if isinstance(result, dict) else list_easy_commands()
        lines = [
            "[RealAI tools — live catalog]",
            data.get("hint") or "",
            f"live_tools={data.get('count')}  aliases={data.get('alias_count')}",
            "",
            "Try:",
        ]
        for ex in data.get("examples") or []:
            lines.append(f"  {ex}")
        lines.append("")
        lines.append("Short aliases:")
        for row in (data.get("commands") or [])[:25]:
            lines.append(f"  {row.get('slash')} → {row.get('tool')}")
        lines.append("")
        lines.append("More: /tool <name> · full list grows as abilities/plugins appear.")
        return "\n".join(lines)

    if not isinstance(result, dict):
        return f"[RealAI {tool}]\n{_clip(result, 2000)}"

    # Prefer explicit live_exec formatting upstream; here handle tool payloads.
    if result.get("live") and "exit_code" in result:
        try:
            from realai.bot.live_exec import format_trace

            return format_trace(result)
        except Exception:
            pass

    lines = [f"[RealAI {tool}]"]

    # hive_status shape
    if tool in ("hive_status", "hive") or (
        result.get("surface") == "hive" and "agents" in result and "coverage" in result
    ):
        agents = result.get("agents") or {}
        cov = (result.get("coverage") or {}).get("coverage") or result.get("coverage") or {}
        organs = result.get("organs") or {}
        missing = agents.get("missing") or []
        lines.append(
            "ok={0}  agents={1}/{2}  organs={3}  coverage={4}%".format(
                result.get("ok", agents.get("ok")),
                len(agents.get("present") or []),
                len(agents.get("required") or []) or agents.get("count"),
                organs.get("organ_count"),
                cov.get("weighted_pct") or cov.get("coverage", {}).get("weighted_pct")
                if isinstance(cov.get("coverage"), dict)
                else cov.get("weighted_pct"),
            )
        )
        if missing:
            lines.append("missing agents: " + ", ".join(missing))
        present = agents.get("present") or []
        if present:
            lines.append("present: " + ", ".join(present[:12]))
        by = (cov.get("by_status") if isinstance(cov, dict) else None) or {}
        if by:
            lines.append(
                "abilities: LIVE={0} PARTIAL={1} SOFT={2}".format(
                    by.get("LIVE"), by.get("PARTIAL"), by.get("SOFT")
                )
            )
        lines.append("Tip: /hive-run <task> · /coverage · /agents · /tools")
        return "\n".join(str(x) for x in lines if x is not None)

    # coverage (nested under coverage_summary().coverage)
    cov = result.get("coverage") if isinstance(result.get("coverage"), dict) else result
    if tool in ("ability_coverage", "coverage") or (
        isinstance(cov, dict) and ("weighted_pct" in cov or "by_status" in cov)
    ):
        by = (cov.get("by_status") if isinstance(cov, dict) else None) or {}
        lines.append(
            "coverage={0}%  abilities={1}  LIVE={2} PARTIAL={3} SOFT={4}".format(
                (cov or {}).get("weighted_pct") if isinstance(cov, dict) else None,
                (cov or {}).get("ability_count")
                if isinstance(cov, dict)
                else result.get("ability_count"),
                by.get("LIVE"),
                by.get("PARTIAL"),
                by.get("SOFT"),
            )
        )
        if result.get("tools_cli"):
            tc = result["tools_cli"]
            lines.append(
                "cli={0} plugins={1}".format(
                    tc.get("path"),
                    ",".join(tc.get("plugins") or [])[:80],
                )
            )
        return "\n".join(lines)

    # agents list
    if tool in ("list_agents",) or (isinstance(result.get("agents"), list) and "count" in result):
        lines.append(f"count={result.get('count')}")
        for a in (result.get("agents") or [])[:12]:
            if isinstance(a, dict):
                lines.append(f"  - {a.get('id')}: {a.get('role') or a.get('preferred_model') or ''}")
            else:
                lines.append(f"  - {a}")
        return "\n".join(lines)

    # lora
    if tool == "list_lora_adapters" or "adapters" in result:
        ads = result.get("adapters") or result.get("lora") or []
        if isinstance(ads, list):
            lines.append(f"adapters={len(ads)}")
            for a in ads[:15]:
                if isinstance(a, dict):
                    lines.append(f"  - {a.get('name') or a.get('id') or a.get('path') or a}")
                else:
                    lines.append(f"  - {a}")
            return "\n".join(lines)

    # health
    if tool == "local_llama_health" or ("status" in result and "vulkan" in str(result).lower()):
        lines.append(_clip(json.dumps(result, default=str), 800))
        return "\n".join(lines)

    # self_heal compact
    if tool in ("self_heal_status", "heal") or result.get("service") == "realai-self-heal":
        lines.append(
            "enabled={0}  root={1}".format(result.get("enabled"), result.get("root"))
        )
        loop = result.get("loop") or []
        if isinstance(loop, list) and loop:
            lines.append("loop:")
            for step in loop[:6]:
                lines.append(f"  - {_clip(step, 100)}")
        lines.append("Tip: /tool self_heal_assemble · /tool self_heal_promote_dry")
        return "\n".join(lines)

    # agents_surface compact
    if tool in ("agents_surface",) or (result.get("ability") == "agents_surface"):
        agents = result.get("hive_agents") or result.get("agents") or []
        lines.append(
            "ok={0} hive_mode={1} agents={2}".format(
                result.get("ok"), result.get("hive_mode"), len(agents) if isinstance(agents, list) else "?"
            )
        )
        if isinstance(agents, list):
            for a in agents[:10]:
                if isinstance(a, dict):
                    lines.append(f"  - {a.get('id')}: {a.get('role')}")
        return "\n".join(lines)

    # generic compact
    if result.get("ok") is False or result.get("error"):
        lines.append(f"ok=false  error={_clip(result.get('error') or result, 400)}")
        return "\n".join(lines)

    # surface list results
    if result.get("ok") and any(k in result for k in ("items", "routes", "plugins", "modules", "organs", "path")):
        summary_keys = [
            k
            for k in (
                "ok",
                "surface",
                "action",
                "count",
                "path",
                "device",
                "status",
                "organ_count",
                "complete",
            )
            if k in result
        ]
        bits = [f"{k}={result.get(k)}" for k in summary_keys]
        if bits:
            lines.append("  ".join(bits))
        for key in ("items", "plugins", "modules", "ids", "routes"):
            val = result.get(key)
            if isinstance(val, list):
                lines.append(f"{key}({len(val)}): " + ", ".join(_clip(str(x), 40) for x in val[:12]))
            elif isinstance(val, dict):
                lines.append(f"{key}: " + ", ".join(list(val.keys())[:16]))
        # avoid dumping huge nested hive_orchestrator
        if len(lines) == 1:
            lines.append(_clip(json.dumps(result, default=str), 1200))
        return "\n".join(lines)

    body = json.dumps(result, indent=2, default=str)
    if len(body) > 1800:
        body = body[:1800] + "\n…(truncated — ask for a field or use /tool with a narrower action)"
    lines.append(body)
    return "\n".join(lines)


def try_easy_tool(text: str, run_tool: Callable[[str, Dict[str, Any]], Any]) -> Optional[Dict[str, Any]]:
    """Parse + execute. Returns operator-style {surface, result, tool} or None."""
    parsed = parse_easy_tool(text)
    if parsed is None:
        return None
    tool, args = parsed
    if tool == "__list__":
        return {"surface": "tools", "tool": "__list__", "result": list_easy_commands()}
    try:
        result = run_tool(tool, args)
    except Exception as exc:
        result = {"ok": False, "error": str(exc), "tool": tool}
    return {"surface": "tool", "tool": tool, "result": result}
