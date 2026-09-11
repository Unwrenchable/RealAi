"""World Model Benchmark rewritten 2026-08-30 for RealAI static reconstruction.

Purpose:
    Validate the core world-model APIs:
        - WorldState.observe / set_fact / get_fact
        - GoalTracker.add_goal / list_goals
        - PlanningEngine.plan

This benchmark does not require a model and performs deterministic checks.
No original bench_world_model.py body was recovered from any scanned tree.
"""

from __future__ import annotations

from typing import Any

from benchmarks.base import BaseBenchmark, BenchmarkResult


def _import_world_model():
    """Try both canonical RealAI import paths."""
    try:
        from realai.world_model import (
            WorldState,
            GoalTracker,
            PlanningEngine,
        )
        return WorldState, GoalTracker, PlanningEngine
    except ImportError:
        try:
            from realai.benchmarks.world_model import (
                WorldState,
                GoalTracker,
                PlanningEngine,
            )
            return WorldState, GoalTracker, PlanningEngine
        except ImportError:
            return None, None, None


class WorldModelBenchmark(BaseBenchmark):
    name = "world_model"

    def run(self, model: Any = None) -> BenchmarkResult:
        WorldState, GoalTracker, PlanningEngine = _import_world_model()

        if not WorldState:
            return BenchmarkResult(
                name=self.name,
                score=0.0,
                total=1,
                passed=0,
                details=[{"error": "world_model import failed"}],
            )

        total = 3
        passed = 0
        details = []

        # --- Test 1: WorldState fact handling ---
        state = WorldState()
        state.observe("The capital of France is Paris", confidence=1.0, source="bench")
        state.set_fact("capital_france", "Paris", 1.0)
        fact_ok = state.get_fact("capital_france") == "Paris"
        passed += bool(fact_ok)
        details.append({"test": "world_state_fact", "passed": fact_ok})

        # --- Test 2: GoalTracker basic goal creation ---
        tracker = GoalTracker()
        goal = tracker.add_goal("Build a REST API", sub_goals=["Design", "Implement"])
        listed = tracker.list_goals()
        goal_ok = goal is not None and len(listed) >= 1
        passed += bool(goal_ok)
        details.append({"test": "goal_tracker_add", "passed": goal_ok})

        # --- Test 3: PlanningEngine basic planning ---
        engine = PlanningEngine()
        steps = engine.plan("Build a REST API", state, max_steps=3)
        plan_ok = isinstance(steps, list) and len(steps) > 0
        passed += bool(plan_ok)
        details.append({"test": "planning_engine_plan", "passed": plan_ok})

        return BenchmarkResult(
            name=self.name,
            score=passed / total,
            total=total,
            passed=passed,
            details=details,
        )