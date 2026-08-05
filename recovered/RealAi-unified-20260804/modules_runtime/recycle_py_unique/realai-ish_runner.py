"""
RealAI Benchmark Runner
========================
Runs all benchmarks and produces a consolidated JSON report.

Usage::

    from benchmarks.runner import run_all_benchmarks

    report = run_all_benchmarks()
    print(report["overall_score"])

CLI::

    python -m benchmarks.runner
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from benchmarks.base import BenchmarkResult


def run_all_benchmarks(model: Any = None) -> Dict[str, Any]:
    """Run all registered benchmarks and return a consolidated report.

    Args:
        model: Optional RealAI model instance for live testing.

    Returns:
        Dict with "benchmarks" list and "overall_score" float.
    """
    from benchmarks.bench_reasoning import ReasoningBenchmark
    from benchmarks.bench_coding import CodingBenchmark
    from benchmarks.bench_safety import SafetyBenchmark
    from benchmarks.bench_tool_use import ToolUseBenchmark
    from benchmarks.bench_memory import MemoryBenchmark
    from benchmarks.bench_agent import AgentBenchmark

    benchmarks = [
        ReasoningBenchmark(),
        CodingBenchmark(),
        SafetyBenchmark(),
        ToolUseBenchmark(),
        MemoryBenchmark(),
        AgentBenchmark(),
    ]

    results: List[Dict[str, Any]] = []
    scores: List[float] = []

    for bench in benchmarks:
        try:
            result = bench.run(model=model)
        except Exception as e:
            result = BenchmarkResult(
                name=bench.name,
                score=0.0,
                total=1,
                passed=0,
                details=[{"error": str(e)}],
            )

        results.append({
            "name": result.name,
            "score": result.score,
            "total": result.total,
            "passed": result.passed,
            "details": result.details,
        })
        scores.append(result.score)

    overall = sum(scores) / len(scores) if scores else 0.0

    return {
        "benchmarks": results,
        "overall_score": round(overall, 3),
    }


def main() -> None:
    """CLI entry point: run all benchmarks and print JSON report."""
    report = run_all_benchmarks()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
