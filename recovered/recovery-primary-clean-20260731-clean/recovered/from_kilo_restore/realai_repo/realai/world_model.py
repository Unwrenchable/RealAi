"""
RealAI World Model Layer
=========================
Provides WorldState, PlanningEngine, GoalTracker, and BeliefUpdater.

Usage::

    from realai.world_model import WORLD_STATE, GOAL_TRACKER, PLANNING_ENGINE

    goal = GOAL_TRACKER.add_goal(
        "Build a REST API",
        sub_goals=["Design", "Implement", "Test"],
    )
    plan = PLANNING_ENGINE.plan("Build a REST API", WORLD_STATE, max_steps=3)
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Goal:
    """A tracked goal with status and optional sub-goals.

    Attributes:
        id: Unique goal identifier.
        description: Human-readable goal description.
        status: One of pending/in_progress/completed/blocked.
        sub_goals: List of sub-goal IDs.
        deadline: Optional Unix deadline timestamp.
        created_at: Unix creation timestamp.
    """

    id: str
    description: str
    status: str = "pending"
    sub_goals: List[str] = field(default_factory=list)
    deadline: Optional[float] = None
    created_at: float = field(default_factory=time.time)


@dataclass
class Observation:
    """A world observation from an external or internal source.

    Attributes:
        id: Unique observation identifier.
        content: Observation text.
        confidence: Confidence in the observation (0.0-1.0).
        source: Optional source identifier.
        timestamp: Unix timestamp.
    """

    id: str
    content: str
    confidence: float = 1.0
    source: str = ""
    timestamp: float = field(default_factory=time.time)


class WorldState:
    """Maintains the agent's current belief about the world.

    Provides a simple key-value interface for quick fact access and tracks
    observations for the BeliefUpdater.
    """

    def __init__(self) -> None:
        """Initialize an empty world state."""
        self._facts: Dict[str, Dict[str, Any]] = {}
        self._observations: List[Observation] = []

    def observe(
        self,
        content: str,
        confidence: float = 1.0,
        source: str = "",
    ) -> Observation:
        """Record a new observation.

        Args:
            content: Observation text content.
            confidence: Confidence level (0.0-1.0).
            source: Optional source identifier.

        Returns:
            The created Observation object.
        """
        obs = Observation(
            id=str(uuid.uuid4()),
            content=content,
            confidence=confidence,
            source=source,
            timestamp=time.time(),
        )
        self._observations.append(obs)
        return obs

    def get_fact(self, key: str) -> Optional[Any]:
        """Retrieve a fact value by key.

        Args:
            key: Fact key.

        Returns:
            The fact value, or None if not found.
        """
        entry = self._facts.get(key)
        return entry["value"] if entry else None

    def set_fact(self, key: str, value: Any, confidence: float = 1.0) -> None:
        """Set a world fact.

        Args:
            key: Fact key.
            value: Fact value.
            confidence: Confidence level (0.0-1.0).
        """
        self._facts[key] = {"value": value, "confidence": confidence}

    def all_facts(self) -> Dict[str, Any]:
        """Return all facts as a plain dict.

        Returns:
            Dict mapping key -> {"value": ..., "confidence": ...}.
        """
        return dict(self._facts)


class PlanningEngine:
    """Generates step-by-step plans from natural language goals.

    Uses template-based decomposition without LLM calls.
    """

    _KEYWORD_MAP = {
        "research": "Search for information about {goal}",
        "code": "Write code to implement {goal}",
        "analyze": "Analyze the requirements for {goal}",
        "deploy": "Deploy the solution for {goal}",
        "test": "Write and run tests for {goal}",
        "design": "Create a design document for {goal}",
        "review": "Review and validate {goal}",
        "document": "Write documentation for {goal}",
    }

    def plan(
        self,
        goal: str,
        current_state: Any,
        max_steps: int = 5,
    ) -> List[Dict[str, Any]]:
        """Generate a plan to achieve a goal.

        Args:
            goal: Description of the goal.
            current_state: WorldState instance (not used in template mode).
            max_steps: Maximum number of steps to generate.

        Returns:
            List of step dicts with "step", "action", and "rationale" keys.
        """
        goal_lower = goal.lower()
        steps = []

        # Match keywords in the goal
        for keyword, template in self._KEYWORD_MAP.items():
            if keyword in goal_lower:
                action = template.format(goal=goal)
                steps.append({
                    "step": len(steps) + 1,
                    "action": action,
                    "rationale": "Goal mentions '{0}'".format(keyword),
                })
                if len(steps) >= max_steps:
                    break

        # Default steps if no keywords matched
        if not steps:
            default_actions = [
                "Break down the goal: {0}".format(goal),
                "Research relevant information for: {0}".format(goal),
                "Create an action plan for: {0}".format(goal),
                "Execute the plan for: {0}".format(goal),
                "Verify and validate: {0}".format(goal),
            ]
            for i, action in enumerate(default_actions[:max_steps]):
                steps.append({
                    "step": i + 1,
                    "action": action,
                    "rationale": "Default planning step",
                })

        return steps[:max_steps]


class GoalTracker:
    """Tracks goals and their sub-goals with status management.

    Stores goals in memory; provides CRUD and status update operations.
    """

    def __init__(self) -> None:
        """Initialize an empty goal tracker."""
        self._goals: Dict[str, Goal] = {}

    def add_goal(
        self,
        description: str,
        sub_goals: Optional[List[str]] = None,
        deadline: Optional[float] = None,
    ) -> Goal:
        """Create and track a new goal.

        Args:
            description: Human-readable goal description.
            sub_goals: Optional list of sub-goal descriptions (creates sub-goals).
            deadline: Optional Unix deadline timestamp.

        Returns:
            The created Goal object.
        """
        goal_id = str(uuid.uuid4())
        sub_goal_ids = []

        for sub_desc in (sub_goals or []):
            sub_goal = Goal(
                id=str(uuid.uuid4()),
                description=sub_desc,
                created_at=time.time(),
            )
            self._goals[sub_goal.id] = sub_goal
            sub_goal_ids.append(sub_goal.id)

        goal = Goal(
            id=goal_id,
            description=description,
            sub_goals=sub_goal_ids,
            deadline=deadline,
            created_at=time.time(),
        )
        self._goals[goal_id] = goal
        return goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Retrieve a goal by ID.

        Args:
            goal_id: Goal ID to look up.

        Returns:
            Goal or None.
        """
        return self._goals.get(goal_id)

    def update_status(self, goal_id: str, status: str) -> bool:
        """Update a goal's status.

        Args:
            goal_id: Goal ID to update.
            status: New status string (pending/in_progress/completed/blocked).

        Returns:
            True if found and updated, False otherwise.
        """
        goal = self._goals.get(goal_id)
        if goal is None:
            return False
        goal.status = status
        return True

    def list_goals(self, status: Optional[str] = None) -> List[Goal]:
        """Return all goals, optionally filtered by status.

        Args:
            status: Optional status filter.

        Returns:
            List of matching Goal objects.
        """
        if status is None:
            return list(self._goals.values())
        return [g for g in self._goals.values() if g.status == status]

    def add_sub_goal(self, parent_id: str, description: str) -> Optional[Goal]:
        """Add a sub-goal to an existing goal.

        Args:
            parent_id: Parent goal ID.
            description: Sub-goal description.

        Returns:
            The created sub-Goal, or None if parent not found.
        """
        parent = self._goals.get(parent_id)
        if parent is None:
            return None
        sub_goal = Goal(
            id=str(uuid.uuid4()),
            description=description,
            created_at=time.time(),
        )
        self._goals[sub_goal.id] = sub_goal
        parent.sub_goals.append(sub_goal.id)
        return sub_goal


class BeliefUpdater:
    """Updates world state beliefs from new observations.

    Extracts key-value pairs from observation content and merges
    with confidence-weighted blending.
    """

    _KV_PATTERNS = [
        re.compile(r"(\w[\w\s]*?)\s+is\s+(.+?)(?:\.|,|$)", re.IGNORECASE),
        re.compile(r"(\w[\w\s]*?)\s*=\s*(.+?)(?:\.|,|$)", re.IGNORECASE),
    ]

    def update(self, state: WorldState, observation: Observation) -> None:
        """Extract facts from an observation and update world state.

        Args:
            state: WorldState to update.
            observation: New Observation to process.
        """
        for pattern in self._KV_PATTERNS:
            for match in pattern.finditer(observation.content):
                key = match.group(1).strip().lower().replace(" ", "_")
                value = match.group(2).strip()

                # Confidence-weighted merge
                existing = state._facts.get(key)
                if existing:
                    new_confidence = (
                        existing["confidence"] * 0.7
                        + observation.confidence * 0.3
                    )
                    state.set_fact(key, value, new_confidence)
                else:
                    state.set_fact(key, value, observation.confidence)


# ---------------------------------------------------------------------------
# Global singletons
# ---------------------------------------------------------------------------

WORLD_STATE = WorldState()
GOAL_TRACKER = GoalTracker()
PLANNING_ENGINE = PlanningEngine()
