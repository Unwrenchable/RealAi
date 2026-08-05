"""Memory benchmark: tests MemoryEngine store and retrieve."""

from __future__ import annotations

from typing import Any

from benchmarks.base import BaseBenchmark, BenchmarkResult


class MemoryBenchmark(BaseBenchmark):
    """Tests MemoryEngine store+retrieve recall."""

    name = "memory"

    def run(self, model: Any = None) -> BenchmarkResult:
        """Store items and check they can be retrieved.

        Args:
            model: Unused.

        Returns:
            BenchmarkResult with recall accuracy.
        """
        try:
            from realai.memory.engine import MemoryEngine
        except ImportError:
            return BenchmarkResult(
                name=self.name,
                score=0.0,
                total=1,
                passed=0,
                details=[{"error": "Could not import MemoryEngine"}],
            )

        engine = MemoryEngine()
        test_items = [
            ("The capital of France is Paris", ["geography"]),
            ("Python is a programming language", ["tech"]),
            ("The speed of light is 299792458 m/s", ["physics"]),
        ]

        stored_ids = []
        for content, tags in test_items:
            item_id = engine.store(content, tags=tags)
            stored_ids.append(item_id)

        passed = 0
        details = []

        # Test retrieval
        results = engine.retrieve("Paris capital France", top_k=5)
        found = any("Paris" in item.content for item in results)
        if found:
            passed += 1
        details.append({
            "test": "retrieve_geography",
            "passed": found,
            "results_count": len(results),
        })

        # Test forget
        success = engine.forget(stored_ids[0])
        if success:
            passed += 1
        details.append({
            "test": "forget_item",
            "passed": success,
        })

        # Test short-term memory length
        recent = engine.short_term.get_recent(10)
        # We stored 3; forget() removes from short-term too, so expect >= 2
        has_items = len(recent) >= 2
        if has_items:
            passed += 1
        details.append({
            "test": "short_term_recall",
            "passed": has_items,
            "count": len(recent),
        })

        total = 3
        score = passed / total
        return BenchmarkResult(
            name=self.name,
            score=score,
            total=total,
            passed=passed,
            details=details,
        )
