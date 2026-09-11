"""
RealAI Identity Layer
======================
Manages AI personas with creation, switching, training, and persistence.

Usage::

    from realai.identity import IDENTITY_MANAGER, PERSONA_SWITCHER

    persona = IDENTITY_MANAGER.create(
        name="Assistant",
        description="A helpful assistant",
        system_prompt="You are a helpful assistant.",
    )
    result = PERSONA_SWITCHER.switch_to(persona.id)
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PersonaProfile:
    """Profile defining an AI persona.

    Attributes:
        id: Unique persona identifier.
        name: Display name.
        description: Human-readable description.
        system_prompt: System prompt for this persona.
        tone: Interaction tone (balanced/formal/casual/empathetic).
        memory_namespace: Memory namespace for this persona.
        created_at: Unix creation timestamp.
    """

    id: str
    name: str
    description: str
    system_prompt: str
    tone: str = "balanced"
    memory_namespace: str = ""
    created_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        """Set default memory_namespace if not provided."""
        if not self.memory_namespace:
            self.memory_namespace = "persona_{0}".format(self.id)


class IdentityManager:
    """Creates, stores, and manages persona profiles.

    Persists personas to a JSON file in ~/.realai/personas.json.
    """

    def __init__(self, config_path: str = "~/.realai/personas.json") -> None:
        """Initialize the identity manager.

        Args:
            config_path: Path to personas JSON file.
        """
        self._config_path = os.path.expanduser(config_path)
        self._personas: Dict[str, PersonaProfile] = {}
        self._load()

    def create(
        self,
        name: str,
        description: str,
        system_prompt: str,
        tone: str = "balanced",
    ) -> PersonaProfile:
        """Create and persist a new persona.

        Args:
            name: Persona display name.
            description: Persona description.
            system_prompt: System prompt text.
            tone: Interaction tone.

        Returns:
            The created PersonaProfile.
        """
        persona_id = str(uuid.uuid4())
        persona = PersonaProfile(
            id=persona_id,
            name=name,
            description=description,
            system_prompt=system_prompt,
            tone=tone,
            created_at=time.time(),
        )
        self._personas[persona_id] = persona
        self._save()
        return persona

    def get(self, persona_id: str) -> Optional[PersonaProfile]:
        """Retrieve a persona by ID.

        Args:
            persona_id: Persona ID to look up.

        Returns:
            PersonaProfile or None.
        """
        return self._personas.get(persona_id)

    def list_all(self) -> List[PersonaProfile]:
        """Return all personas.

        Returns:
            List of all PersonaProfile objects.
        """
        return list(self._personas.values())

    def update(self, persona_id: str, **kwargs: Any) -> Optional[PersonaProfile]:
        """Update persona fields.

        Args:
            persona_id: Persona ID to update.
            **kwargs: Fields to update (name, description, system_prompt, tone).

        Returns:
            Updated PersonaProfile, or None if not found.
        """
        persona = self._personas.get(persona_id)
        if persona is None:
            return None
        for key, value in kwargs.items():
            if hasattr(persona, key):
                setattr(persona, key, value)
        self._save()
        return persona

    def delete(self, persona_id: str) -> bool:
        """Delete a persona.

        Args:
            persona_id: Persona ID to delete.

        Returns:
            True if found and deleted, False otherwise.
        """
        if persona_id not in self._personas:
            return False
        del self._personas[persona_id]
        self._save()
        return True

    def _save(self) -> None:
        """Persist personas to the config file."""
        try:
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            data = [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "system_prompt": p.system_prompt,
                    "tone": p.tone,
                    "memory_namespace": p.memory_namespace,
                    "created_at": p.created_at,
                }
                for p in self._personas.values()
            ]
            with open(self._config_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save personas: %s", e)

    def _load(self) -> None:
        """Load personas from the config file."""
        if not os.path.exists(self._config_path):
            return
        try:
            with open(self._config_path, "r") as f:
                data = json.load(f)
            for item in (data if isinstance(data, list) else []):
                persona = PersonaProfile(
                    id=item.get("id", str(uuid.uuid4())),
                    name=item.get("name", ""),
                    description=item.get("description", ""),
                    system_prompt=item.get("system_prompt", ""),
                    tone=item.get("tone", "balanced"),
                    memory_namespace=item.get("memory_namespace", ""),
                    created_at=item.get("created_at", time.time()),
                )
                self._personas[persona.id] = persona
        except Exception as e:
            logger.warning("Failed to load personas: %s", e)


class PersonaSwitcher:
    """Manages active persona switching.

    Maintains the currently active persona and provides its system prompt.
    """

    def __init__(
        self,
        manager: IdentityManager,
        memory_engine: Any = None,
    ) -> None:
        """Initialize the persona switcher.

        Args:
            manager: IdentityManager instance.
            memory_engine: Optional MemoryEngine for namespace switching.
        """
        self._manager = manager
        self._memory_engine = memory_engine
        self.active: Optional[PersonaProfile] = None

    def switch_to(self, persona_id: str) -> Dict[str, Any]:
        """Activate a persona by ID.

        Args:
            persona_id: ID of the persona to activate.

        Returns:
            Dict with switched_to and namespace, or error if not found.
        """
        persona = self._manager.get(persona_id)
        if persona is None:
            return {"error": "Persona not found: {0}".format(persona_id)}
        self.active = persona
        return {
            "switched_to": persona.name,
            "namespace": persona.memory_namespace,
        }

    def get_active_system_prompt(self) -> str:
        """Return the active persona's system prompt.

        Returns:
            System prompt string, or default prompt if no persona is active.
        """
        if self.active:
            return self.active.system_prompt
        return "You are a helpful AI assistant."


class PersonaTrainer:
    """Collects feedback and suggests persona prompt improvements.

    Stores feedback in memory and uses simple heuristics to suggest updates.
    """

    def __init__(self) -> None:
        """Initialize the persona trainer."""
        self._feedback: Dict[str, List[Dict[str, Any]]] = {}

    def collect_feedback(
        self,
        persona_id: str,
        interaction: str,
        rating: int,
    ) -> None:
        """Record a feedback entry for a persona.

        Args:
            persona_id: Persona ID to associate feedback with.
            interaction: Interaction text.
            rating: Integer rating (e.g. 1-5).
        """
        if persona_id not in self._feedback:
            self._feedback[persona_id] = []
        self._feedback[persona_id].append({
            "interaction": interaction,
            "rating": rating,
            "timestamp": time.time(),
        })

    def suggest_prompt_update(
        self,
        persona_id: str,
        manager: IdentityManager,
    ) -> str:
        """Suggest a system prompt update based on feedback patterns.

        Args:
            persona_id: Persona ID to analyze.
            manager: IdentityManager for current persona data.

        Returns:
            Suggested system prompt string.
        """
        persona = manager.get(persona_id)
        if persona is None:
            return ""

        feedback_list = self._feedback.get(persona_id, [])
        if not feedback_list:
            return persona.system_prompt

        avg_rating = sum(f["rating"] for f in feedback_list) / len(feedback_list)

        if avg_rating >= 4:
            return persona.system_prompt  # Good as is

        # Suggest an improvement
        suggestion = (
            "{original} Always provide clear, detailed, and helpful responses. "
            "Based on {count} feedback items with average rating {avg:.1f}.".format(
                original=persona.system_prompt,
                count=len(feedback_list),
                avg=avg_rating,
            )
        )
        return suggestion

    def apply_suggestion(
        self,
        persona_id: str,
        suggestion: str,
        manager: IdentityManager,
    ) -> bool:
        """Apply a suggested prompt update to a persona.

        Args:
            persona_id: Persona ID to update.
            suggestion: New system prompt string.
            manager: IdentityManager to apply the update through.

        Returns:
            True if applied successfully, False if persona not found.
        """
        result = manager.update(persona_id, system_prompt=suggestion)
        return result is not None


# ---------------------------------------------------------------------------
# Global singletons
# ---------------------------------------------------------------------------

IDENTITY_MANAGER = IdentityManager()
PERSONA_SWITCHER = PersonaSwitcher(IDENTITY_MANAGER)
