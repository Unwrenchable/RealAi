# AURA - Core Skills

from .registry import Skill

class NoOpSkill(Skill):
    """A skill that does nothing. Used as a fallback."""

    @property
    def name(self) -> str:
        return "core.noop"

    def execute(self, **kwargs) -> str:
        """Does nothing and returns a confirmation."""
        return "No action was taken."
