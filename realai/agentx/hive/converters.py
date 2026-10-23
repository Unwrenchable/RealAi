"""Convert legacy agent definitions into .agentx manifest dicts (schema/agent.schema.json)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_FM = re.compile(r"^\ufeff?---\s*\n(.*?)\n---\s*(?:\n|$)", re.S)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "agent"


def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """Minimal YAML front-matter parser (scalars, folded '>' blocks, [a, b] and '- x' lists)."""
    m = _FM.match(text.replace("\r\n", "\n"))
    if not m:
        return {}, text
    body = text.replace("\r\n", "\n")[m.end():]
    meta: dict[str, Any] = {}
    key = None
    for line in m.group(1).split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        km = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if km and not line.startswith((" ", "\t")):
            key, val = km.group(1), km.group(2).strip()
            if val in (">", "|", ">-", "|-", ""):
                meta[key] = "" if val else []
            elif val.startswith("[") and val.endswith("]"):
                meta[key] = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
            else:
                meta[key] = val.strip("'\"")
            continue
        if key is None:
            continue
        item = line.strip()
        if item.startswith("- "):
            if not isinstance(meta.get(key), list):
                meta[key] = []
            meta[key].append(item[2:].strip().strip("'\""))
        elif isinstance(meta.get(key), str):
            meta[key] = (meta[key] + " " + item).strip()
        elif meta.get(key) == []:
            meta[key] = item
    return meta, body


def _base(agent_id: str, role: str, description: str) -> dict[str, Any]:
    return {
        "id": agent_id,
        "role": role,
        "description": description,
        "goals": [],
        "input_format": {"type": "text"},
        "output_format": {"type": "text"},
        "tools_allowed": [],
        "memory_policy": {"adapter": "json", "namespace": agent_id, "use_global": True,
                          "use_agent_local": True, "max_history": 10},
        "routing_tags": [],
        "provider_preferences": ["local", "realai"],
    }


def agent_md_to_manifest(path: Path, agent_id: str | None = None) -> dict[str, Any] | None:
    """Return a manifest for a Copilot `.agent.md`/agent `.md`, or None if it has no front-matter name."""
    meta, body = parse_front_matter(path.read_text(encoding="utf-8", errors="replace"))
    name = str(meta.get("name") or "").strip()
    if not name:
        return None
    stem = path.name.split(".")[0]
    aid = agent_id or _slug(stem if stem not in {"my-agent", "agent"} else name)
    description = str(meta.get("description") or "").strip()
    raw = _base(aid, name, description)
    tools = meta.get("tools") or []
    raw["tools_allowed"] = [str(t) for t in tools] if isinstance(tools, list) else []
    words = re.findall(r"[a-z0-9]+", (name + " " + description).lower())
    stop = {"the", "and", "for", "with", "a", "of", "to", "in", "on", "who", "that", "your", "from", "all"}
    raw["routing_tags"] = sorted({w for w in words if len(w) > 3 and w not in stop})[:12]
    raw["goals"] = [description] if description else [name]
    raw["source"] = {"kind": "agent.md", "path": str(path), "prompt_chars": len(body)}
    return raw


def hive_role_json_to_manifest(path: Path) -> dict[str, Any] | None:
    """Convert a RealAI hive role file (.github/agents/<role>.json) to a manifest."""
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None
    return role_dict_to_manifest(data, path)


def role_dict_to_manifest(data: Any, path: Path | str = "", kind: str = "hive-role-json") -> dict[str, Any] | None:
    """Convert a role dict (hive role JSON or agent-tools catalog entry) to a manifest."""
    if not isinstance(data, dict) or not data.get("id"):
        return None
    raw = _base(str(data["id"]), str(data.get("role") or data["id"]), str(data.get("description") or ""))
    raw["tools_allowed"] = [str(t) for t in data.get("required_tools") or []]
    raw["routing_tags"] = [str(t) for t in (data.get("tags") or []) + (data.get("capabilities") or [])]
    raw["goals"] = [str(c) for c in data.get("capabilities") or []] or [raw["role"]]
    raw["profile"] = str(data.get("preferred_profile") or "safe")
    raw["risk_level"] = str(data.get("risk_level") or "low")
    raw["hive"] = bool(data.get("hive", True))
    if data.get("preferred_model"):
        raw["preferred_model"] = str(data["preferred_model"])
    raw["source"] = {"kind": kind, "path": str(path)}
    raw["legacy"] = data
    return raw
