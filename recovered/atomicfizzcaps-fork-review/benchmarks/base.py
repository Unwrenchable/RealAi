"""
RealAI Benchmark Base
======================
Abstract base class for all RealAI benchmarks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class BenchmarkResult:
    """Result from a benchmark run.

    Attributes:
        name: Benchmark name.
        score: Overall score (0.0-1.0).
        total: Total test cases.
        passed: Passing test cases.
        details: Per-test detail dicts.
    """

    name: str
    score: float
    total: int
    passed: int
    details: List[Dict[str, Any]] = field(default_factory=list)


class BaseBenchmark:
    """Abstract base class for all benchmarks.

    Subclasses must define the ``name`` class attribute and implement ``run()``.
    """

    name: str = "base"

    def run(self, model: Any = None) -> BenchmarkResult:
        """Execute the benchmark.

        Args:
            model: Optional RealAI model instance for live testing.

        Returns:
            BenchmarkResult with score and details.

        Raises:
            NotImplementedError: Subclasses must implement this.
        """
        raise NotImplementedError("Subclasses must implement run()")

    def report(self, result: BenchmarkResult) -> str:
        """Format a benchmark result as a human-readable string.

        Args:
            result: BenchmarkResult to format.

        Returns:
            Formatted string report.
        """
        return (
            "[{name}] Score: {score:.2f} | "
            "Passed: {passed}/{total}".format(
                name=result.name,
                score=result.score,
                passed=result.passed,
                total=result.total,
            )
        )
