"""
RealAI Intelligent Provider Router
====================================
Routes AI requests to optimal providers based on capability, cost, speed,
and availability. Includes per-provider circuit breakers.

Usage::

    from realai.router import INTELLIGENT_ROUTER

    provider = INTELLIGENT_ROUTER.select_provider("chat", ["openai", "anthropic"])
    # "openai" or "anthropic" — highest composite score
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


@dataclass
class ProviderScore:
    """Composite score for a provider for a given task type.

    Attributes:
        provider: Provider name string.
        capability_score: Score 0.0-1.0 for task capability.
        cost_score: Score 0.0-1.0 (higher = cheaper).
        speed_score: Score 0.0-1.0.
        availability_score: Score 0.0-1.0.
        preference_score: Score 0.0-1.0 (user/config preference).
        composite_score: Weighted composite (computed via compute_composite()).
    """

    provider: str
    capability_score: float
    cost_score: float
    speed_score: float
    availability_score: float
    preference_score: float
    composite_score: float = 0.0

    def compute_composite(self) -> float:
        """Compute the weighted composite score.

        Weights: capability * 0.40 + cost * 0.20 + speed * 0.15 +
                 availability * 0.15 + preference * 0.10.

        Returns:
            Composite score float, also stored in self.composite_score.
        """
        self.composite_score = (
            self.capability_score * 0.40
            + self.cost_score * 0.20
            + self.speed_score * 0.15
            + self.availability_score * 0.15
            + self.preference_score * 0.10
        )
        return self.composite_score


class CircuitState(Enum):
    """Possible states of a circuit breaker.

    Attributes:
        CLOSED: Normal operation — requests pass through.
        OPEN: Circuit is tripped — requests fail fast.
        HALF_OPEN: Recovery probe — one test request allowed.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Per-provider circuit breaker with sliding-window failure counting.

    Tracks recent successes and failures within a configurable time window.
    Trips to OPEN when the failure threshold is reached or the error rate
    exceeds error_rate_threshold. Automatically transitions to HALF_OPEN
    after recovery_probe_secs so a single probe request can test recovery.
    """

    def __init__(
        self,
        provider: str,
        failure_threshold: int = 5,
        error_rate_threshold: float = 0.5,
        window_secs: float = 60.0,
        recovery_probe_secs: float = 30.0,
    ) -> None:
        """Initialize the circuit breaker.

        Args:
            provider: Name of the provider this breaker protects.
            failure_threshold: Number of failures within the window before tripping.
            error_rate_threshold: Failure ratio (0.0-1.0) that triggers the trip.
            window_secs: Sliding window duration in seconds.
            recovery_probe_secs: Seconds in OPEN state before allowing a probe.
        """
        self._provider = provider
        self._failure_threshold = failure_threshold
        self._error_rate_threshold = error_rate_threshold
        self._window_secs = window_secs
        self._recovery_probe_secs = recovery_probe_secs
        self._state: CircuitState = CircuitState.CLOSED
        self._failure_times: deque = deque()
        self._success_times: deque = deque()
        self._opened_at: float = 0.0

    def _evict_old(self) -> None:
        """Remove events older than the sliding window."""
        cutoff = time.time() - self._window_secs
        while self._failure_times and self._failure_times[0] < cutoff:
            self._failure_times.popleft()
        while self._success_times and self._success_times[0] < cutoff:
            self._success_times.popleft()

    def record_success(self) -> None:
        """Record a successful request.

        Resets failure counters and transitions back to CLOSED if in HALF_OPEN.
        """
        self._success_times.append(time.time())
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            self._failure_times.clear()
        self._evict_old()

    def record_failure(self) -> None:
        """Record a failed request.

        Trips the circuit if the failure threshold or error rate is exceeded.
        """
        now = time.time()
        self._failure_times.append(now)
        self._evict_old()

        failures = len(self._failure_times)
        total = failures + len(self._success_times)
        error_rate = failures / total if total > 0 else 0.0

        if failures >= self._failure_threshold or error_rate >= self._error_rate_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = now

    def is_available(self) -> bool:
        """Return True if requests may be sent to this provider.

        Returns:
            True when state is CLOSED or HALF_OPEN; False when OPEN.
        """
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.OPEN:
            if time.time() - self._opened_at >= self._recovery_probe_secs:
                self._state = CircuitState.HALF_OPEN
                return True
            return False
        # HALF_OPEN
        return True

    def get_state(self) -> CircuitState:
        """Return the current circuit state.

        Also triggers OPEN → HALF_OPEN transition if recovery time has elapsed.

        Returns:
            Current CircuitState.
        """
        # Trigger probe transition
        self.is_available()
        return self._state


class IntelligentRouter:
    """Routes requests to the optimal AI provider.

    Scores providers using a weighted composite of capability, cost, speed,
    availability (circuit breaker status), and preference. Maintains
    per-provider CircuitBreaker instances.
    """

    DEFAULT_CAPABILITY_RULES: Dict[str, Dict[str, float]] = {
        "openai": {
            "chat": 0.95, "code": 0.95, "image": 0.90,
            "embedding": 0.95, "audio": 0.90, "default": 0.85,
        },
        "anthropic": {
            "chat": 0.95, "code": 0.90, "analysis": 0.95, "default": 0.85,
        },
        "gemini": {"chat": 0.85, "image": 0.85, "default": 0.80},
        "openrouter": {"chat": 0.80, "default": 0.75},
        "mistral": {"chat": 0.80, "code": 0.80, "default": 0.75},
        "together": {"chat": 0.75, "default": 0.70},
        "local": {"chat": 0.60, "code": 0.65, "default": 0.55},
    }

    DEFAULT_COST_SCORES: Dict[str, float] = {
        "local": 1.0,
        "together": 0.85,
        "openrouter": 0.80,
        "mistral": 0.75,
        "gemini": 0.70,
        "openai": 0.50,
        "anthropic": 0.45,
    }

    DEFAULT_SPEED_SCORES: Dict[str, float] = {
        "local": 0.90,
        "together": 0.80,
        "openai": 0.75,
        "gemini": 0.75,
        "mistral": 0.70,
        "openrouter": 0.65,
        "anthropic": 0.60,
    }

    def __init__(self, routing_rules: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the router with optional custom routing rules.

        Args:
            routing_rules: Optional dict to override default capability rules.
                Format: {provider: {task_type: score_float, ...}, ...}
        """
        self._capability_rules: Dict[str, Dict[str, float]] = dict(
            self.DEFAULT_CAPABILITY_RULES
        )
        if routing_rules:
            for provider, rules in routing_rules.items():
                if provider in self._capability_rules:
                    self._capability_rules[provider].update(rules)
                else:
                    self._capability_rules[provider] = rules

        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._preference_scores: Dict[str, float] = {}

    def _get_circuit_breaker(self, provider: str) -> CircuitBreaker:
        """Get or create a CircuitBreaker for a provider.

        Args:
            provider: Provider name.

        Returns:
            CircuitBreaker instance for the provider.
        """
        if provider not in self._circuit_breakers:
            self._circuit_breakers[provider] = CircuitBreaker(provider)
        return self._circuit_breakers[provider]

    def score_providers(
        self,
        task_type: str,
        available_providers: List[str],
    ) -> List[ProviderScore]:
        """Score each provider for the given task type.

        Args:
            task_type: Task type string (e.g. "chat", "code", "image").
            available_providers: List of provider names to score.

        Returns:
            List of ProviderScore objects sorted by composite_score descending.
        """
        scores: List[ProviderScore] = []

        for provider in available_providers:
            cap_map = self._capability_rules.get(provider, {})
            capability = cap_map.get(task_type, cap_map.get("default", 0.5))

            cost = self.DEFAULT_COST_SCORES.get(provider, 0.5)
            speed = self.DEFAULT_SPEED_SCORES.get(provider, 0.5)

            cb = self._get_circuit_breaker(provider)
            availability = 1.0 if cb.is_available() else 0.0

            preference = self._preference_scores.get(provider, 0.5)

            ps = ProviderScore(
                provider=provider,
                capability_score=capability,
                cost_score=cost,
                speed_score=speed,
                availability_score=availability,
                preference_score=preference,
            )
            ps.compute_composite()
            scores.append(ps)

        scores.sort(key=lambda s: s.composite_score, reverse=True)
        return scores

    def select_provider(
        self,
        task_type: str,
        available_providers: Optional[List[str]] = None,
    ) -> str:
        """Select the best available provider for a task type.

        Args:
            task_type: Task type string.
            available_providers: Providers to consider. Defaults to all known providers.

        Returns:
            Provider name string of the selected provider.
            Falls back to "openai" if no providers are available.
        """
        if available_providers is None:
            available_providers = list(self._capability_rules.keys())

        scored = self.score_providers(task_type, available_providers)

        for ps in scored:
            cb = self._get_circuit_breaker(ps.provider)
            if cb.is_available():
                return ps.provider

        # All providers down — return highest-scored anyway
        return scored[0].provider if scored else "openai"

    def record_success(self, provider: str) -> None:
        """Record a successful request to a provider.

        Args:
            provider: Provider name.
        """
        self._get_circuit_breaker(provider).record_success()

    def record_failure(self, provider: str) -> None:
        """Record a failed request to a provider.

        Args:
            provider: Provider name.
        """
        self._get_circuit_breaker(provider).record_failure()

    def get_circuit_status(self) -> Dict[str, str]:
        """Return the circuit state for all tracked providers.

        Returns:
            Dict mapping provider name -> CircuitState.value string.
        """
        return {
            provider: cb.get_state().value
            for provider, cb in self._circuit_breakers.items()
        }


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

INTELLIGENT_ROUTER = IntelligentRouter()
