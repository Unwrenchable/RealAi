"""
RealAI Safety Layer
===================
Lightweight, pluggable input/output filters and tool-safety enforcement.

Design goals
------------
* Zero hard dependencies — pure Python, no additional installs required.
* Non-blocking by default: ``check_input`` and ``check_output`` return a
  ``SafetyResult`` that callers can inspect and act on, rather than raising
  immediately.
* Extensible: register custom ``InputRule`` / ``OutputRule`` objects at
  runtime via ``SafetyFilter.register_input_rule()`` / ``register_output_rule()``.

Usage::

    from realai.safety import SAFETY_FILTER

    result = SAFETY_FILTER.check_input("Tell me how to make a bomb")
    if result.blocked:
        # return a refusal instead of continuing
        ...

    out_result = SAFETY_FILTER.check_output(response_text)
    if out_result.flagged:
        # redact or warn
        ...
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class SafetyResult:
    """Result from a safety check."""
    blocked: bool = False          # hard block — do not proceed
    flagged: bool = False          # soft flag — proceed but log/warn
    reason: str = ""               # human-readable explanation
    rule_id: str = ""              # which rule triggered
    redacted_text: Optional[str] = None  # sanitised version when applicable

    @property
    def ok(self) -> bool:
        """True when neither blocked nor flagged."""
        return not self.blocked and not self.flagged


@dataclass
class InputRule:
    """A single input safety rule."""
    id: str
    description: str
    check: Callable[[str], SafetyResult]


@dataclass
class OutputRule:
    """A single output safety rule."""
    id: str
    description: str
    check: Callable[[str], SafetyResult]


# ---------------------------------------------------------------------------
# Built-in rules
# ---------------------------------------------------------------------------

_HARD_BLOCK_PATTERNS: List[str] = [
    r"\b(make|build|create|synthesise?|synthesize)\s+(a\s+)?(bomb|explosive|weapon|malware|ransomware|trojan)\b",
    r"\b(hack|exploit|bypass)\s+(a\s+)?(password|auth|2fa|mfa|firewall)\b",
    r"\b(how\s+to|steps?\s+to)\s+(kill|murder|assault)\b",
    r"\bchild\s+(porn|sex|abuse|exploitation)\b",
]

_SOFT_FLAG_PATTERNS: List[str] = [
    r"\b(crack|brute.?force)\b",
    r"\b(doxx|dox|stalking|tracking)\b",
    r"\bpersonal\s+(address|location|phone)\b",
]

_PII_PATTERNS: List[str] = [
    r"\b\d{3}-\d{2}-\d{4}\b",                          # SSN
    r"\b(?:\d[ -]?){13,16}\b",                         # credit card
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",  # email
]


def _make_pattern_rule(
    rule_id: str,
    description: str,
    patterns: List[str],
    hard_block: bool,
) -> InputRule:
    compiled = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in patterns]

    def _check(text: str) -> SafetyResult:
        for pat in compiled:
            m = pat.search(text)
            if m:
                return SafetyResult(
                    blocked=hard_block,
                    flagged=not hard_block,
                    reason=f"Matched safety pattern: {pat.pattern[:60]}",
                    rule_id=rule_id,
                )
        return SafetyResult()

    return InputRule(id=rule_id, description=description, check=_check)


def _pii_output_rule() -> OutputRule:
    compiled = [re.compile(p, re.IGNORECASE) for p in _PII_PATTERNS]

    def _check(text: str) -> SafetyResult:
        redacted = text
        found = False
        for pat in compiled:
            if pat.search(redacted):
                found = True
                redacted = pat.sub("[REDACTED]", redacted)
        if found:
            return SafetyResult(
                flagged=True,
                reason="Output contains potential PII — redacted.",
                rule_id="output-pii",
                redacted_text=redacted,
            )
        return SafetyResult()

    return OutputRule(id="output-pii", description="Redact PII from model output.", check=_check)


# ---------------------------------------------------------------------------
# SafetyFilter
# ---------------------------------------------------------------------------

class SafetyFilter:
    """Composite safety filter that applies all registered rules in order.

    Rules are applied sequentially.  The first ``blocked=True`` result is
    returned immediately (short-circuit).  Flagged results accumulate — the
    returned ``SafetyResult`` reflects the most severe flag found.
    """

    def __init__(self) -> None:
        self._input_rules: List[InputRule] = [
            _make_pattern_rule(
                "input-hard-block",
                "Block clearly harmful or illegal requests.",
                _HARD_BLOCK_PATTERNS,
                hard_block=True,
            ),
            _make_pattern_rule(
                "input-soft-flag",
                "Flag borderline requests for logging.",
                _SOFT_FLAG_PATTERNS,
                hard_block=False,
            ),
        ]
        self._output_rules: List[OutputRule] = [
            _pii_output_rule(),
        ]

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_input_rule(self, rule: InputRule) -> None:
        """Append a custom input rule."""
        self._input_rules.append(rule)

    def register_output_rule(self, rule: OutputRule) -> None:
        """Append a custom output rule."""
        self._output_rules.append(rule)

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def check_input(self, text: str) -> SafetyResult:
        """Run all input rules against ``text``.

        Returns immediately on the first hard block.
        """
        worst = SafetyResult()
        for rule in self._input_rules:
            result = rule.check(text)
            if result.blocked:
                return result
            if result.flagged and not worst.flagged:
                worst = result
        return worst

    def check_output(self, text: str) -> SafetyResult:
        """Run all output rules against ``text``.

        Returns immediately on the first hard block.
        Accumulates flags; the ``redacted_text`` of the last redacting rule wins.
        """
        worst = SafetyResult()
        for rule in self._output_rules:
            result = rule.check(text)
            if result.blocked:
                return result
            if result.flagged and not worst.flagged:
                worst = result
            elif result.redacted_text:
                worst = result
        return worst

    def check_tool_call(self, agent_id: str, tool_name: str,
                        allowed_tools: List[str]) -> SafetyResult:
        """Enforce tool-allow-list for a given agent.

        Args:
            agent_id: The agent requesting the tool.
            tool_name: The tool being invoked.
            allowed_tools: The agent's ``tools_allowed`` list.

        Returns:
            SafetyResult with ``blocked=True`` if the tool is not allowed.
        """
        if allowed_tools and tool_name not in allowed_tools:
            return SafetyResult(
                blocked=True,
                reason=f"Agent '{agent_id}' is not allowed to use tool '{tool_name}'.",
                rule_id="tool-allow-list",
            )
        return SafetyResult()

    # ------------------------------------------------------------------
    # Refusal helper
    # ------------------------------------------------------------------

    def refusal_message(self, result: SafetyResult) -> Dict[str, Any]:
        """Return a standard refusal response dict for a blocked request."""
        return {
            "status": "blocked",
            "reason": result.reason,
            "rule_id": result.rule_id,
            "message": (
                "I'm sorry, I can't help with that request. "
                "It appears to violate RealAI's safety policies. "
                "Please rephrase or choose a different topic."
            ),
        }


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

SAFETY_FILTER = SafetyFilter()
