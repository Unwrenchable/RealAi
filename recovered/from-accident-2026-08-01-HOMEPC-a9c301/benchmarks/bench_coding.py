"""Coding benchmark: tests generate_code() responses."""

from __future__ import annotations

from typing import Any

from benchmarks.base import BaseBenchmark, BenchmarkResult


class CodingBenchmark(BaseBenchmark):
    """Tests that generate_code() returns responses with a 'code' field.

    Uses 3 coding tasks.
    """

    name = "coding"

    _TASKS = [
        {
            "language": "python",
            "description": "Write a function that returns the factorial of n",
        },
        {
            "language": "python",
            "description": "Write a function to check if a string is a palindrome",
        },
        {
            "language": "python",
            "description": "Write a function that sorts a list using bubble sort",
        },
    ]

    def run(self, model: Any = None) -> BenchmarkResult:
        """Run coding tasks against a model or stub.

        Args:
            model: Optional RealAI model. If None, uses placeholder responses.

        Returns:
            BenchmarkResult with per-task details.
        """
        passed = 0
        details = []

        for task in self._TASKS:
            if model is not None:
                try:
                    response = model.generate_code(
                        prompt=task["description"],
                        language=task["language"],
                    )
                    has_code = "code" in response or "content" in response
                except Exception as e:
                    has_code = False
                    response = {"error": str(e)}
            else:
                response = {
                    "code": "def placeholder(): pass",
                    "language": task["language"],
                }
                has_code = True

            if has_code:
                passed += 1
            details.append({
                "task": task["description"][:60],
                "language": task["language"],
                "passed": has_code,
            })

        total = len(self._TASKS)
        score = passed / total if total > 0 else 0.0
        return BenchmarkResult(
            name=self.name,
            score=score,
            total=total,
            passed=passed,
            details=details,
        )
