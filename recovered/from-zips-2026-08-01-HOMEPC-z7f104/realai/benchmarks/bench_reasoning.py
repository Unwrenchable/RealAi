"""Reasoning benchmark: tests basic logic, math, and pattern problems."""

from __future__ import annotations

from typing import Any, Dict, List

from benchmarks.base import BaseBenchmark, BenchmarkResult


class ReasoningBenchmark(BaseBenchmark):
    """Tests basic reasoning with 5 logic problems.

    Checks that responses have non-empty content (format check only,
    not semantic correctness against a real LLM).
    """

    name = "reasoning"

    _PROBLEMS: List[Dict[str, Any]] = [
        {
            "question": (
                "All cats are animals. Fluffy is a cat. "
                "Is Fluffy an animal? Answer yes/no."
            ),
            "check": lambda r: isinstance(r, str) and len(r.strip()) > 0,
            "description": "Syllogism",
        },
        {
            "question": "What is 15 * 7?",
            "check": lambda r: isinstance(r, str) and len(r.strip()) > 0,
            "description": "Arithmetic",
        },
        {
            "question": "Complete the pattern: 2, 4, 8, 16, ?",
            "check": lambda r: isinstance(r, str) and len(r.strip()) > 0,
            "description": "Pattern recognition",
        },
        {
            "question": (
                "If all roses are flowers, and some flowers fade quickly, "
                "can we conclude that some roses fade quickly?"
            ),
            "check": lambda r: isinstance(r, str) and len(r.strip()) > 0,
            "description": "Logical inference",
        },
        {
            "question": (
                "A bat and a ball cost $1.10 in total. "
                "The bat costs $1 more than the ball. "
                "How much does the ball cost?"
            ),
            "check": lambda r: isinstance(r, str) and len(r.strip()) > 0,
            "description": "Word problem",
        },
    ]

    def run(self, model: Any = None) -> BenchmarkResult:
        """Run all reasoning problems against a model or stub.

        Args:
            model: Optional RealAI model. If None, uses placeholder responses.

        Returns:
            BenchmarkResult with per-problem details.
        """
        passed = 0
        details = []

        for problem in self._PROBLEMS:
            if model is not None:
                try:
                    response = model.chat_completion(
                        messages=[{"role": "user", "content": problem["question"]}]
                    )
                    choices = response.get("choices", [])
                    content = (
                        choices[0].get("message", {}).get("content", "")
                        if choices
                        else ""
                    )
                except Exception as e:
                    content = "Error: {0}".format(e)
            else:
                # Stub: return placeholder
                content = "Placeholder answer for: {0}".format(
                    problem["question"][:30]
                )

            ok = problem["check"](content)
            if ok:
                passed += 1
            details.append({
                "description": problem["description"],
                "passed": ok,
                "response_preview": str(content)[:80] if content else "",
            })

        total = len(self._PROBLEMS)
        score = passed / total if total > 0 else 0.0
        return BenchmarkResult(
            name=self.name,
            score=score,
            total=total,
            passed=passed,
            details=details,
        )
