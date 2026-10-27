"""Single agent registry for the hive: .agentx manifests + converted legacy definitions."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from realai.agentx.engine.loader import AgentManifest, AgentManifestLoader, validate_agent_manifest

from .converters import agent_md_to_manifest, hive_role_json_to_manifest, role_dict_to_manifest

PKG = Path(__file__).resolve().parents[1]
DATA = PKG / "data"


def product_root() -> Path:
    return PKG.parents[1]


def to_manifest(raw: dict[str, Any]) -> AgentManifest:
    errors = validate_agent_manifest(raw)
    if errors:
        raise ValueError(f"invalid manifest {raw.get('id')!r}: {errors}")
    return AgentManifest(
        id=raw["id"], role=raw["role"], goals=list(raw["goals"]),
        input_format=dict(raw["input_format"]), output_format=dict(raw["output_format"]),
        tools_allowed=list(raw["tools_allowed"]), memory_policy=dict(raw["memory_policy"]),
        routing_tags=list(raw["routing_tags"]), description=str(raw.get("description", "")),
        provider_preferences=list(raw.get("provider_preferences", [])), skills=list(raw.get("skills", [])),
    )


@dataclass
class HiveRegistry:
    manifests: dict[str, AgentManifest] = field(default_factory=dict)
    raw: dict[str, dict[str, Any]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    hive_roles: list[dict[str, Any]] = field(default_factory=list)

    def add(self, raw: dict[str, Any], overwrite: bool = False) -> None:
        aid = raw.get("id")
        if not aid or (aid in self.manifests and not overwrite):
            return
        try:
            self.manifests[aid] = to_manifest(raw)
            self.raw[aid] = raw
        except ValueError as exc:
            self.errors.append(str(exc))

    def hive_role_dicts(self) -> list[dict[str, Any]]:
        """Legacy shape used by hive_router.register_routes (dicts with 'id')."""
        return [dict(r) for r in self.hive_roles]


def load_registry(agent_dirs: Iterable[Path] | None = None, include_builtin: bool = True,
                  include_catalog: bool = True) -> HiveRegistry:
    reg = HiveRegistry()
    if include_builtin:
        for m in AgentManifestLoader(DATA / "agents").load_agents(force=True).values():
            reg.add({"id": m.id, "role": m.role, "goals": m.goals, "input_format": m.input_format,
                     "output_format": m.output_format, "tools_allowed": m.tools_allowed,
                     "memory_policy": m.memory_policy, "routing_tags": m.routing_tags,
                     "description": m.description, "provider_preferences": m.provider_preferences,
                     "skills": m.skills, "source": {"kind": "agentx"}})
    dirs = list(agent_dirs) if agent_dirs is not None else [product_root() / ".github" / "agents"]
    for d in dirs:
        d = Path(d)
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.json")):
            raw = hive_role_json_to_manifest(p)
            if raw:
                reg.hive_roles.append(dict(raw["legacy"]))
                if raw["id"] in reg.manifests:
                    raw = dict(raw, id=f"hive-{raw['id']}")
                reg.add(raw)
        for p in sorted(d.glob("*.md")):
            raw = agent_md_to_manifest(p)
            if raw:
                reg.add(raw)
        for p in sorted(d.glob("*.agentx")):
            import json
            try:
                reg.add(json.loads(p.read_text(encoding="utf-8")))
            except Exception as exc:  # pragma: no cover
                reg.errors.append(f"{p}: {exc}")
    if include_catalog and (DATA / "catalog_agents.json").is_file():
        import json as _json
        for entry in _json.loads((DATA / "catalog_agents.json").read_text(encoding="utf-8")):
            raw = role_dict_to_manifest(entry, DATA / "catalog_agents.json", kind="agentx-catalog")
            if raw:
                reg.add(raw)
    return reg
