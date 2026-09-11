"""Canonical filename: bench_stack_health.py

RECONSTRUCTED 2026-08-30. No original body existed.
Related: scanners/stack_health.py (static path presence) and
unresolved benchmarks/bench_stack.py from the 1:39 AM Grok drop.

This benchmark only reports stack_health.check() results.
It does not start servers, training, dispatch, or import RealAI runtime.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

STATUS = "reconstructed_static"
CANONICAL_NAME = "bench_stack_health"
RECOVERED_FROM = "scanners/stack_health.py"

try:
    from benchmarks.base import BaseBenchmark, BenchmarkResult
except ImportError:
    BaseBenchmark = object  # type: ignore

    class BenchmarkResult:  # type: ignore
        def __init__(self, name: str, score: float, total: int, passed: int, details: Optional[List[Dict[str, Any]]] = None) -> None:
            self.name = name
            self.score = score
            self.total = total
            self.passed = passed
            self.details = details or []


class StackHealthBenchmark(BaseBenchmark):
    """Static presence check via stack_health.check if importable."""

    name = "stack_health"

    def run(self, model: Any = None) -> BenchmarkResult:
        try:
            from scanners.stack_health import check
            report = check()
        except ImportError:
            try:
                from realai.scanners.stack_health import check  # type: ignore
                report = check()
            except ImportError:
                return BenchmarkResult(
                    name=self.name,
                    score=0.0,
                    total=1,
                    passed=0,
                    details=[{"error": "stack_health.check not importable", "executed_runtime": False}],
                )

        present = list(report.get("present") or [])
        missing = list(report.get("missing") or [])
        total = max(len(present) + len(missing), 1)
        passed = len(present)
        return BenchmarkResult(
            name=self.name,
            score=passed / total,
            total=total,
            passed=passed,
            details=[{"present": present, "missing": missing, "executed_runtime": False}],
        )
