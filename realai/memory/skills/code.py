# AURA - Code Introspection and Modification Skills

import os
from .registry import Skill

class IntrospectSkill(Skill):
    """A skill to read Aura's own source code files."""

    @property
    def name(self) -> str:
        return "code.introspect"

    def execute(self, filename: str) -> str:
        """Reads one of Aura's internal files."""
        # Security: Ensure the path is within the 'aura' directory
        base_path = os.path.abspath("aura")
        target_path = os.path.abspath(os.path.join(base_path, filename))

        if not target_path.startswith(base_path):
            return "Error: Access denied. Can only read files within the 'aura' directory."

        if not os.path.exists(target_path):
            return f"Error: File not found at '{target_path}'"

        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file '{filename}': {e}"

class ModifySkill(Skill):
    """A skill to modify Aura's own source code files."""

    @property
    def name(self) -> str:
        return "code.modify"

    def execute(self, filename: str, new_content: str) -> str:
        """Writes new content to one of Aura's internal files."""
        # Security: Ensure the path is within the 'aura' directory
        base_path = os.path.abspath("aura")
        target_path = os.path.abspath(os.path.join(base_path, filename))

        if not target_path.startswith(base_path):
            return "Error: Access denied. Can only modify files within the 'aura' directory."

        try:
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return f"Successfully modified file '{filename}'. The change will be active on next restart."
        except Exception as e:
            return f"Error writing to file '{filename}': {e}"
