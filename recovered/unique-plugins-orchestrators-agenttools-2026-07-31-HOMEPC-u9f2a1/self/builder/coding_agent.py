import os
from pathlib import Path

from realai.self_builder import SelfBuilder
from realai.repo_tools import workspace_root


class CodingAgent:
    """Local-first coding agent — uses RealAI server, not paid provider APIs."""

    def __init__(self, api_url=None):
        self.workspace = str(workspace_root())
        self._builder = SelfBuilder(api_url=api_url or os.environ.get("REALAI_API_URL"))

    async def code(self, task: str, file_path: str = None):
        """Run a self-builder task against this repo."""
        print(f"[RealAI Coding Agent] Working on: {task}")
        extra = ""
        if file_path:
            try:
                rel = Path(file_path)
                if not rel.is_absolute():
                    rel = Path(self.workspace) / rel
                extra = f"Focus file: {file_path}\n\n{rel.read_text(encoding='utf-8')[:8000]}"
            except OSError:
                pass
        result = self._builder.run(task, extra_context=extra)
        print("\n" + "=" * 60)
        print(result.get("summary") or result)
        print("=" * 60)
        return result

# Quick usage
if __name__ == "__main__":
    import asyncio
    agent = CodingAgent()
    asyncio.run(agent.code("Create a new function to generate wasteland NPC dialogue"))
