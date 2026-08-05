# AURA - Skill Registry and Base Class

from abc import ABC, abstractmethod

class Skill(ABC):
    """Abstract base class for all skills."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the skill."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Executes the skill with the given parameters."""
        pass

class SkillRegistry:
    """
    Manages the collection of available skills.
    """
    def __init__(self):
        self._skills = {}
        self.load_skills()

    def load_skills(self):
        """Dynamically loads all available skills."""
        # Import skills here to avoid circular dependencies
        from . import file_io, web, core, code

        self.register(file_io.ReadFileSkill())
        self.register(file_io.WriteFileSkill())
        self.register(web.WebSearchSkill())
        self.register(core.NoOpSkill())
        self.register(code.IntrospectSkill())
        self.register(code.ModifySkill())

    def register(self, skill_instance: Skill):
        """Registers a skill instance."""
        if skill_instance.name in self._skills:
            print(f"Warning: Skill '{skill_instance.name}' is being overwritten.")
        self._skills[skill_instance.name] = skill_instance
        print(f"Skill registered: {skill_instance.name}")

    def get_skill(self, name: str) -> Skill:
        """Retrieves a skill by its name."""
        return self._skills.get(name)

    def has_skill(self, name: str) -> bool:
        """Checks if a skill is registered."""
        return name in self._skills

    def list_skills(self) -> list:
        """Returns a list of all registered skill names."""
        return list(self._skills.keys())
