"""Agent benchmark: tests AgentRegistry.execute_agent() completes without error."""

from __future__ import annotations

from typing import Any

from benchmarks.base import BaseBenchmark, BenchmarkResult


class AgentBenchmark(BaseBenchmark):
    """Tests that AgentRegistry can execute an agent task."""

    name = "agent"

    def run(self, model: Any = None) -> BenchmarkResult:
        """Execute a simple agent task.

        Args:
            model: Unused.

        Returns:
            BenchmarkResult indicating success or failure.
        """
        try:
            from realai import AgentRegistry
        except ImportError:
            return BenchmarkResult(
                name=self.name,
                score=0.0,
                total=1,
                passed=0,
                details=[{"error": "Could not import AgentRegistry"}],
            )

        passed = 0
        details = []

        try:
            registry = AgentRegistry()
            result = registry.execute_agent(
                agent_id="test-agent",
                task="Test task: summarize the concept of machine learning",
            )
            # Just check it returns a dict without error
            success = isinstance(result, dict)
            if success:
                passed += 1
            details.append({
                "test": "execute_agent",
                "passed": success,
                "result_keys": list(result.keys()) if isinstance(result, dict) else [],
            })
        except Exception as e:
            details.append({
                "test": "execute_agent",
                "passed": False,
                "error": str(e),
            })

        total = 1
        score = passed / total
        return BenchmarkResult(
            name=self.name,
            score=score,
            total=total,
            passed=passed,
            details=details,
        )
