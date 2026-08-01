"""Tool use benchmark: validates TOOL_REGISTRY schemas and ToolCallValidator."""

from __future__ import annotations

from typing import Any

from benchmarks.base import BaseBenchmark, BenchmarkResult


class ToolUseBenchmark(BaseBenchmark):
    """Tests ToolRegistry schema validity and ToolCallValidator correctness."""

    name = "tool_use"

    def run(self, model: Any = None) -> BenchmarkResult:
        """Validate all registered tools and test the validator.

        Args:
            model: Unused.

        Returns:
            BenchmarkResult with per-tool details.
        """
        try:
            from realai.tools import TOOL_REGISTRY, ToolCallValidator
        except ImportError:
            return BenchmarkResult(
                name=self.name,
                score=0.0,
                total=1,
                passed=0,
                details=[{"error": "Could not import realai.tools"}],
            )

        tools = TOOL_REGISTRY.list_all()
        passed = 0
        details = []

        for tool in tools:
            valid = bool(
                tool.name
                and tool.description
                and isinstance(tool.parameters, dict)
            )
            if valid:
                passed += 1
            details.append({
                "tool": tool.name,
                "has_name": bool(tool.name),
                "has_description": bool(tool.description),
                "has_parameters": isinstance(tool.parameters, dict),
                "passed": valid,
            })

        # Test validator with a known valid call
        validator = ToolCallValidator()
        val_result = validator.validate("web_research", {"query": "test"})
        if val_result.valid:
            passed += 1
        details.append({
            "test": "validator_web_research",
            "passed": val_result.valid,
            "errors": val_result.errors,
        })

        total = len(tools) + 1
        score = passed / total if total > 0 else 0.0
        return BenchmarkResult(
            name=self.name,
            score=score,
            total=total,
            passed=passed,
            details=details,
        )
