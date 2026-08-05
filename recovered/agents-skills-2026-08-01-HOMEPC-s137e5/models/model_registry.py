"""
RealAI Model Registry
=====================
Centralised, machine-readable catalogue of known models with capabilities,
compatibility matrices, performance profiles, and routing policies.

Usage::

    from realai.model_registry import MODEL_REGISTRY, get_model_metadata

    meta = get_model_metadata("realai-1.0-agentic")
    print(meta["context_window"])   # 128000
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


_METADATA_PATH = Path(__file__).resolve().parent / "models" / "metadata.json"


@dataclass
class ModelMetadata:
    """Metadata for a single model in the RealAI ecosystem."""

    id: str
    name: str
    display_name: str = ""
    owned_by: str = "realai"
    description: str = ""
    context_window: int = 8192
    max_output_tokens: int = 4096
    training_cutoff: str = "2024-01"
    modalities: List[str] = field(default_factory=lambda: ["text"])
    tool_calling: bool = False
    structured_output: bool = False
    cost_score: int = 2
    speed_score: int = 3
    quality_score: int = 3
    local_available: bool = False
    family: str = "realai"
    tier: str = "general"
    default: bool = False
    capabilities: List[str] = field(default_factory=list)
    compatibility_matrix: Dict[str, Any] = field(default_factory=dict)
    performance_profile: Dict[str, Any] = field(default_factory=dict)
    routing_policies: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelMetadata":
        """Construct metadata from machine-readable JSON."""
        item = dict(data)
        item.setdefault("display_name", item.get("name", item.get("id", "")))
        return cls(**item)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the model metadata."""
        return {
            "id": self.id,
            "object": "model",
            "name": self.name,
            "display_name": self.display_name or self.name,
            "owned_by": self.owned_by,
            "description": self.description,
            "context_window": self.context_window,
            "max_output_tokens": self.max_output_tokens,
            "training_cutoff": self.training_cutoff,
            "modalities": self.modalities,
            "tool_calling": self.tool_calling,
            "structured_output": self.structured_output,
            "cost_score": self.cost_score,
            "speed_score": self.speed_score,
            "quality_score": self.quality_score,
            "local_available": self.local_available,
            "family": self.family,
            "tier": self.tier,
            "default": self.default,
            "capabilities": self.capabilities,
            "compatibility_matrix": self.compatibility_matrix,
            "performance_profile": self.performance_profile,
            "routing_policies": self.routing_policies,
        }

    def routing_priority_for(self, capability: str) -> int:
        """Return explicit routing priority for a capability, if present."""
        policy = self.routing_policies.get(capability, {})
        return int(policy.get("priority", 0))


def _load_metadata() -> Dict[str, Any]:
    """Load machine-readable model metadata from disk."""
    return json.loads(_METADATA_PATH.read_text(encoding="utf-8"))


_METADATA = _load_metadata()
_DECLARED_CAPABILITIES: List[str] = list(_METADATA.get("capabilities", []))
_MODELS: List[ModelMetadata] = [
    ModelMetadata.from_dict(item) for item in _METADATA.get("models", [])
]


class CapabilityGraph:
    """Maps capability strings to sorted lists of (model_id, score) tuples."""

    def __init__(self, models: List[ModelMetadata], declared_capabilities: Optional[List[str]] = None) -> None:
        self._graph: Dict[str, List[tuple[str, float]]] = {
            cap: [] for cap in (declared_capabilities or [])
        }
        for model in models:
            for cap in model.capabilities:
                self._graph.setdefault(cap, [])
                score = (
                    model.routing_priority_for(cap),
                    model.quality_score,
                    model.speed_score,
                    model.context_window,
                )
                composite = float(score[0]) + (score[1] * 0.1) + (score[2] * 0.01)
                self._graph[cap].append((model.id, composite))
        for cap in self._graph:
            self._graph[cap].sort(key=lambda x: x[1], reverse=True)

    def get(self, capability: str) -> List[tuple[str, float]]:
        """Return sorted (model_id, score) list for a capability."""
        return self._graph.get(capability, [])

    def all_capabilities(self) -> List[str]:
        """Return all known capability strings."""
        return sorted(self._graph.keys())

    def to_dict(self) -> Dict[str, Any]:
        """Return capability graph as a plain machine-readable dict."""
        return {
            cap: [
                {"model_id": model_id, "score": score}
                for model_id, score in entries
            ]
            for cap, entries in self._graph.items()
        }


class ModelRegistry:
    """In-memory catalogue of all known models.

    Provides lookup, filtering by family/provider, capability routing, and
    machine-readable registry payloads for API consumers.
    """

    def __init__(self, models: Optional[List[ModelMetadata]] = None) -> None:
        self._models: Dict[str, ModelMetadata] = {m.id: m for m in (models or _MODELS)}

    def get(self, model_id: str) -> Optional[ModelMetadata]:
        return self._models.get(model_id)

    def list_all(self) -> List[ModelMetadata]:
        return list(self._models.values())

    def list_by_family(self, family: str) -> List[ModelMetadata]:
        return [m for m in self._models.values() if m.family == family]

    def list_by_owner(self, owned_by: str) -> List[ModelMetadata]:
        return [m for m in self._models.values() if m.owned_by == owned_by]

    def list_capabilities(self) -> List[str]:
        dynamic = {cap for model in self._models.values() for cap in model.capabilities}
        return sorted(set(_DECLARED_CAPABILITIES) | dynamic)

    def get_default_model(self) -> Optional[ModelMetadata]:
        for model in self._models.values():
            if model.default:
                return model
        return next(iter(self._models.values()), None)

    def models_with_capability(self, capability: str) -> List[ModelMetadata]:
        return [m for m in self._models.values() if capability in m.capabilities]

    def get_compatibility_matrix(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        if model_id is not None:
            model = self.get(model_id)
            return dict(model.compatibility_matrix) if model else {}
        return {m.id: dict(m.compatibility_matrix) for m in self._models.values()}

    def get_performance_profiles(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        if model_id is not None:
            model = self.get(model_id)
            return dict(model.performance_profile) if model else {}
        return {m.id: dict(m.performance_profile) for m in self._models.values()}

    def get_routing_policies(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        if model_id is not None:
            model = self.get(model_id)
            return dict(model.routing_policies) if model else {}
        return {m.id: dict(m.routing_policies) for m in self._models.values()}

    def best_model_for(
        self,
        capability: str,
        opts: Optional[Dict[str, Any]] = None,
    ) -> Optional[ModelMetadata]:
        opts = opts or {}
        candidates = [
            m
            for m in self._models.values()
            if capability in m.capabilities
            and m.cost_score <= opts.get("max_cost", 5)
            and m.quality_score >= opts.get("min_quality", 1)
            and (not opts.get("need_tools") or m.tool_calling)
            and (not opts.get("prefer_local") or m.local_available)
            and (not opts.get("prefer_owner") or m.owned_by == opts.get("prefer_owner"))
        ]
        if opts.get("prefer_tier"):
            tier_candidates = [m for m in candidates if m.tier == opts["prefer_tier"]]
            if tier_candidates:
                candidates = tier_candidates
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda m: (
                m.routing_priority_for(capability),
                m.quality_score,
                m.speed_score,
                m.context_window,
            ),
        )

    def recommend(
        self,
        prefer_local: bool = False,
        need_tools: bool = False,
        max_cost: int = 5,
        min_quality: int = 1,
        task_type: Optional[str] = None,
    ) -> Optional[ModelMetadata]:
        if task_type is not None:
            routed = self.best_model_for(
                task_type,
                {
                    "prefer_local": prefer_local,
                    "need_tools": need_tools,
                    "max_cost": max_cost,
                    "min_quality": min_quality,
                },
            )
            if routed is not None:
                return routed
        candidates = [
            m for m in self._models.values()
            if m.cost_score <= max_cost
            and m.quality_score >= min_quality
            and (not need_tools or m.tool_calling)
            and (not prefer_local or m.local_available)
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda m: (m.quality_score, m.speed_score, m.context_window))

    def route_for_task(
        self,
        task_type: str,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Optional[ModelMetadata]:
        return self.best_model_for(task_type, constraints or {})

    def register(self, meta: ModelMetadata) -> None:
        self._models[meta.id] = meta

    def to_openai_list(self) -> Dict[str, Any]:
        return {
            "object": "list",
            "data": [
                {
                    "id": m.id,
                    "object": "model",
                    "created": 1708308000,
                    "owned_by": m.owned_by,
                    "permission": [],
                    "root": m.id,
                    "parent": None,
                    "display_name": m.display_name or m.name,
                    "family": m.family,
                    "tier": m.tier,
                    "capabilities": m.capabilities,
                    "context_window": m.context_window,
                    "max_output_tokens": m.max_output_tokens,
                    "default": m.default,
                }
                for m in self.list_all()
            ],
        }

    def to_capabilities_payload(self) -> Dict[str, Any]:
        return {
            "capabilities": self.list_capabilities(),
            "capability_graph": CAPABILITY_GRAPH.to_dict(),
            "default_model": self.get_default_model().id if self.get_default_model() else None,
            "models": [
                {
                    "id": m.id,
                    "display_name": m.display_name or m.name,
                    "family": m.family,
                    "tier": m.tier,
                    "modalities": m.modalities,
                    "capabilities": m.capabilities,
                    "context_window": m.context_window,
                    "max_output_tokens": m.max_output_tokens,
                    "performance_profile": m.performance_profile,
                }
                for m in self.list_all()
            ],
            "routing_policies": self.get_routing_policies(),
        }


MODEL_REGISTRY = ModelRegistry()
CAPABILITY_GRAPH = CapabilityGraph(_MODELS, declared_capabilities=_DECLARED_CAPABILITIES)


def get_model_metadata(model_id: str) -> Optional[Dict[str, Any]]:
    meta = MODEL_REGISTRY.get(model_id)
    return meta.to_dict() if meta else None
