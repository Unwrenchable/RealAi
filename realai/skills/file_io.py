# AURA - File I/O Skills

import os
from .registry import Skill

class ReadFileSkill(Skill):
    """A skill to read the contents of a file."""

    @property
    def name(self) -> str:
        return "file_io.read_file"

    def execute(self, filepath: str) -> str:
        """Reads a file and returns its content."""
        if not os.path.exists(filepath):
            return f"Error: File not found at '{filepath}'"
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file '{filepath}': {e}"

class WriteFileSkill(Skill):
    """A skill to write content to a file."""

    @property
    def name(self) -> str:
        return "file_io.write_file"

    def execute(self, filepath: str, content: str) -> str:
        """Writes content to a file, creating it if necessary."""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote to file '{filepath}'"
        except Exception as e:
            return f"Error writing to file '{filepath}': {e}"
