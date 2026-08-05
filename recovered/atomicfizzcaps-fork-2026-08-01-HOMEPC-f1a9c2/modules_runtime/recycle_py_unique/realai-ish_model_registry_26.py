"""
RealAI Model Registry
=====================
Centralised catalogue of known models with capabilities, context windows,
cost scores, and provider metadata.  Used by the API server, provider router,
and the dashboard to present accurate model information.

Usage::

    from realai.model_registry import MODEL_REGISTRY, get_model_metadata

    meta = get_model_metadata("realai-1.0-agentic")
    print(meta["context_window"])   # 128000

Adding a new model
------------------
Add an entry to ``_MODELS`` below. All fields except ``id`` and ``name``
are optional but encouraged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ModelMetadata:
    """Metadata for a single model in the RealAI ecosystem."""
    id: str
    name: str
    owned_by: str = "realai"
    description: str = ""
    context_window: int = 8192          # max input tokens
    max_output_tokens: int = 4096
    training_cutoff: str = "2024-01"
    modalities: List[str] = field(default_factory=lambda: ["text"])
    tool_calling: bool = False
    structured_output: bool = False
    cost_score: int = 2                 # 1 (cheapest) → 5 (most expensive)
    speed_score: int = 3                # 1 (slowest) → 5 (fastest)
    quality_score: int = 3              # 1 (lowest) → 5 (highest)
    local_available: bool = False       # can be run via local runtime
    family: str = "realai"
    capabilities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "object": "model",
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
            "capabilities": self.capabilities,
        }


# ---------------------------------------------------------------------------
# Model catalogue
# ---------------------------------------------------------------------------

_MODELS: List[ModelMetadata] = [
    # ---- RealAI model family -----------------------------------------------
    ModelMetadata(
        id="realai-2.0",
        name="RealAI 2.0",
        description="General-purpose orchestration model with 110 built-in capabilities.",
        context_window=128_000,
        max_output_tokens=8192,
        training_cutoff="2025-01",
        modalities=["text", "image", "audio", "video"],
        tool_calling=True,
        structured_output=True,
        cost_score=3,
        speed_score=4,
        quality_score=5,
        family="realai",
        capabilities=["coding", "vision", "reasoning", "long-context", "tool-calling", "multimodal"],
    ),
    ModelMetadata(
        id="realai-1.0-base",
        name="RealAI 1.0 Base",
        description="Base pre-trained model — foundation for fine-tuning.",
        context_window=32_768,
        max_output_tokens=4096,
        training_cutoff="2024-06",
        cost_score=1,
        speed_score=5,
        quality_score=3,
        local_available=True,
        family="realai-1.0",
        capabilities=["local", "speed"],
    ),
    ModelMetadata(
        id="realai-1.0-instruct",
        name="RealAI 1.0 Instruct",
        description="Instruction-tuned variant optimised for chat and Q&A.",
        context_window=32_768,
        max_output_tokens=4096,
        training_cutoff="2024-06",
        tool_calling=True,
        cost_score=2,
        speed_score=4,
        quality_score=4,
        local_available=True,
        family="realai-1.0",
        capabilities=["local", "tool-calling"],
    ),
    ModelMetadata(
        id="realai-1.0-agentic",
        name="RealAI 1.0 Agentic",
        description="Agent-native model tuned on tool-call traces and multi-step reasoning.",
        context_window=128_000,
        max_output_tokens=8192,
        training_cutoff="2024-06",
        tool_calling=True,
        structured_output=True,
        cost_score=3,
        speed_score=3,
        quality_score=5,
        local_available=True,
        family="realai-1.0",
        capabilities=["local", "reasoning", "tool-calling", "long-context"],
    ),
    # ---- Third-party models (metadata only — keys not stored here) ----------
    ModelMetadata(
        id="gpt-4o",
        name="GPT-4o",
        owned_by="openai",
        description="OpenAI multimodal flagship model.",
        context_window=128_000,
        max_output_tokens=4096,
        training_cutoff="2024-04",
        modalities=["text", "image"],
        tool_calling=True,
        structured_output=True,
        cost_score=4,
        speed_score=4,
        quality_score=5,
        family="gpt-4",
        capabilities=["vision", "reasoning", "tool-calling", "multimodal"],
    ),
    ModelMetadata(
        id="gpt-4o-mini",
        name="GPT-4o mini",
        owned_by="openai",
        description="Smaller, faster, cheaper OpenAI model.",
        context_window=128_000,
        max_output_tokens=4096,
        training_cutoff="2024-04",
        tool_calling=True,
        cost_score=1,
        speed_score=5,
        quality_score=3,
        family="gpt-4",
        capabilities=["speed", "tool-calling"],
    ),
    ModelMetadata(
        id="claude-3-5-sonnet-20241022",
        name="Claude 3.5 Sonnet",
        owned_by="anthropic",
        description="Anthropic balanced reasoning model.",
        context_window=200_000,
        max_output_tokens=8192,
        training_cutoff="2024-04",
        tool_calling=True,
        structured_output=True,
        cost_score=3,
        speed_score=3,
        quality_score=5,
        family="claude-3.5",
        capabilities=["reasoning", "long-context", "tool-calling"],
    ),
    ModelMetadata(
        id="llama-3.1-8b-instant",
        name="Llama 3.1 8B Instant",
        owned_by="groq",
        description="Meta Llama 3.1 8B served at Groq speed.",
        context_window=128_000,
        max_output_tokens=8192,
        training_cutoff="2023-12",
        cost_score=1,
        speed_score=5,
        quality_score=3,
        local_available=True,
        family="llama-3.1",
        capabilities=["local", "speed"],
    ),
    ModelMetadata(
        id="gemini-1.5-pro",
        name="Gemini 1.5 Pro",
        owned_by="gemini",
        description="Google long-context multimodal model.",
        context_window=1_000_000,
        max_output_tokens=8192,
        training_cutoff="2024-04",
        modalities=["text", "image", "audio"],
        tool_calling=True,
        cost_score=3,
        speed_score=3,
        quality_score=5,
        family="gemini-1.5",
        capabilities=["vision", "reasoning", "long-context", "multimodal"],
    ),
]


class CapabilityGraph:
    """Maps capability strings to sorted lists of (model_id, score) tuples.

    Capability strings: coding, vision, reasoning, long-context, speed,
    tool-calling, multimodal, local, embeddings
    """

    def __init__(self, models: List[ModelMetadata]) -> None:
        """Build the capability graph from a list of model metadata."""
        self._graph: Dict[str, List[tuple]] = {}
        for model in models:
            for cap in model.capabilities:
                if cap not in self._graph:
                    self._graph[cap] = []
                score = (model.quality_score + model.speed_score) / 2.0
                self._graph[cap].append((model.id, score))
        for cap in self._graph:
            self._graph[cap].sort(key=lambda x: x[1], reverse=True)

    def get(self, capability: str) -> List[tuple]:
        """Return sorted (model_id, score) list for a capability."""
        return self._graph.get(capability, [])

    def all_capabilities(self) -> List[str]:
        """Return all known capability strings."""
        return list(self._graph.keys())

    def to_dict(self) -> Dict[str, Any]:
        """Return capability graph as a plain dict."""
        return {cap: list(entries) for cap, entries in self._graph.items()}


class ModelRegistry:
    """In-memory catalogue of all known models.

    Provides lookup, filtering by family/provider, and routing hints.
    """

    def __init__(self) -> None:
        self._models: Dict[str, ModelMetadata] = {m.id: m for m in _MODELS}

    def get(self, model_id: str) -> Optional[ModelMetadata]:
        """Return metadata for a model ID, or ``None`` if unknown."""
        return self._models.get(model_id)

    def list_all(self) -> List[ModelMetadata]:
        """Return all registered models."""
        return list(self._models.values())

    def list_by_family(self, family: str) -> List[ModelMetadata]:
        """Return models matching a family prefix (e.g. 'realai-1.0')."""
        return [m for m in self._models.values() if m.family == family]

    def list_by_owner(self, owned_by: str) -> List[ModelMetadata]:
        """Return models owned by a specific provider."""
        return [m for m in self._models.values() if m.owned_by == owned_by]

    def recommend(
        self,
        prefer_local: bool = False,
        need_tools: bool = False,
        max_cost: int = 5,
        min_quality: int = 1,
        task_type: Optional[str] = None,
    ) -> Optional[ModelMetadata]:
        """Return the best-fit model matching the given constraints.

        Selection is deterministic: highest quality among candidates, then
        highest speed as tiebreaker.

        Args:
            prefer_local: If True, only consider locally available models.
            need_tools: If True, only consider models with tool-calling.
            max_cost: Maximum cost score (1-5).
            min_quality: Minimum quality score (1-5).
            task_type: Optional capability string for task-based routing.
        """
        if task_type is not None:
            constraints = {
                "max_cost": max_cost,
                "min_quality": min_quality,
                "prefer_local": prefer_local,
                "need_tools": need_tools,
            }
            routed = self.route_for_task(task_type, constraints)
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
        return max(candidates, key=lambda m: (m.quality_score, m.speed_score))

    def route_for_task(
        self,
        task_type: str,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Optional[ModelMetadata]:
        """Return the best model for a task type given optional constraints.

        Args:
            task_type: A capability string like "coding" or "vision".
            constraints: Optional dict with keys: max_cost, min_quality,
                         prefer_local, need_tools.

        Returns:
            Best matching ModelMetadata, or None if no model matches.
        """
        if constraints is None:
            constraints = {}
        capable_ids = {mid for mid, _ in CAPABILITY_GRAPH.get(task_type)}
        candidates = [
            m for m in self._models.values()
            if m.id in capable_ids
            and m.cost_score <= constraints.get("max_cost", 5)
            and m.quality_score >= constraints.get("min_quality", 1)
            and (not constraints.get("need_tools") or m.tool_calling)
            and (not constraints.get("prefer_local") or m.local_available)
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda m: (m.quality_score, m.speed_score))

    def register(self, meta: ModelMetadata) -> None:
        """Add or update a model entry at runtime."""
        self._models[meta.id] = meta

    def to_openai_list(self) -> Dict[str, Any]:
        """Return an OpenAI-compatible ``/v1/models`` response payload."""
        return {
            "object": "list",
            "data": [
                {
                    "id": m.id,
                    "object": "model",
                    "owned_by": m.owned_by,
                    "permission": [],
                }
                for m in self._models.values()
            ],
        }


# Global singleton
MODEL_REGISTRY = ModelRegistry()

#: Pre-built capability graph over the default model catalogue.
CAPABILITY_GRAPH = CapabilityGraph(_MODELS)


def get_model_metadata(model_id: str) -> Optional[Dict[str, Any]]:
    """Convenience helper — returns metadata dict or ``None``."""
    meta = MODEL_REGISTRY.get(model_id)
    return meta.to_dict() if meta else None
