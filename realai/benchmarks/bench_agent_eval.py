"""Canonical filename: bench_agent_eval.py

RECONSTRUCTED 2026-08-30 as an alias.
Recovered body: benchmarks/bench_agent.py (AgentBenchmark).
No separate bench_agent_eval.py existed in recovered trees.
"""
from __future__ import annotations

STATUS = "recovered_alias"
CANONICAL_NAME = "bench_agent_eval"
RECOVERED_FROM = "benchmarks/bench_agent.py"

try:
    from benchmarks.bench_agent import *  # noqa: F401, F403
except ImportError:
    try:
        from .bench_agent import *  # type: ignore  # noqa: F401, F403
    except ImportError:
        pass

try:
    from benchmarks.bench_agent import AgentBenchmark as AgentEvalBenchmark  # noqa: F401
except ImportError:
    AgentEvalBenchmark = None  # type: ignore
