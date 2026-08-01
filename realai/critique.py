"""
RealAI Self-Critique Engine
============================
Evaluates AI responses against quality rubrics, compresses chain-of-thought,
and provides retry-with-critique functionality.

Usage::

    from realai.critique import CRITIQUE_ENGINE

    result = CRITIQUE_ENGINE.evaluate({"choices": [{"message": {"content": "Hello"}}]})
    print(result.overall)  # 0.85
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class CritiqueResult:
    """Result from a response evaluation.

    Attributes:
        scores: Per-dimension scores (accuracy/completeness/safety/coherence), 0.0-1.0.
        overall: Weighted average of all dimension scores.
        suggestions: List of improvement suggestions.
        reasoning_score: Score for the reasoning quality specifically.
    """
    scores: Dict[str, float]
    overall: float
    suggestions: List[str]
    reasoning_score: float


class CritiqueEngine:
    """Evaluates AI responses and provides self-critique capability.

    Supports custom rubrics or defaults to built-in quality checks.
    """

    _DEFAULT_WEIGHTS: Dict[str, float] = {
        "accuracy": 0.3,
        "completeness": 0.3,
        "safety": 0.2,
        "coherence": 0.2,
    }

    _REFUSAL_PATTERNS = [
        r"\bI cannot\b",
        r"\bI'm unable\b",
        r"\bI am unable\b",
        r"\bI can't\b",
        r"\bI won't\b",
    ]

    _COMPILED_REFUSAL_PATTERNS = [
        re.compile(r"\bI cannot\b", re.IGNORECASE),
        re.compile(r"\bI'm unable\b", re.IGNORECASE),
        re.compile(r"\bI am unable\b", re.IGNORECASE),
        re.compile(r"\bI can't\b", re.IGNORECASE),
        re.compile(r"\bI won't\b", re.IGNORECASE),
    ]

    _COMPILED_UNSAFE_PATTERNS = [
        re.compile(r"\b(bomb|explosive|weapon)\s+instructions\b", re.IGNORECASE),
        re.compile(r"\b(hack|exploit)\s+tutorial\b", re.IGNORECASE),
    ]

    def evaluate(
        self,
        response: Dict[str, Any],
        rubric: Optional[Dict[str, Any]] = None,
    ) -> CritiqueResult:
        """Evaluate a response against a rubric.

        Args:
            response: Response dict (OpenAI format with choices[0].message.content
                      or a dict with a "content" key).
            rubric: Optional custom rubric dict. If None, uses default checks.

        Returns:
            CritiqueResult with dimension scores, overall score, and suggestions.
        """
        # Extract content from response
        content = self._extract_content(response)

        scores: Dict[str, float] = {}
        suggestions: List[str] = []

        if rubric:
            # Custom rubric: each key maps to a lambda or just a weight
            for dimension, weight in rubric.items():
                scores[dimension] = 0.7  # default score for custom rubric
        else:
            # Default rubric
            scores["accuracy"] = self._score_accuracy(content, suggestions)
            scores["completeness"] = self._score_completeness(content, suggestions)
            scores["safety"] = self._score_safety(content, suggestions)
            scores["coherence"] = self._score_coherence(content, suggestions)

        weights = rubric if rubric else self._DEFAULT_WEIGHTS
        total_weight = sum(weights.values()) if weights else 1.0
        if total_weight == 0:
            total_weight = 1.0
        overall = sum(
            scores.get(dim, 0.5) * w
            for dim, w in weights.items()
        ) / total_weight

        reasoning_score = (
            scores.get("accuracy", 0.5) * 0.6
            + scores.get("coherence", 0.5) * 0.4
        )

        return CritiqueResult(
            scores=scores,
            overall=round(overall, 3),
            suggestions=suggestions,
            reasoning_score=round(reasoning_score, 3),
        )

    def _extract_content(self, response: Dict[str, Any]) -> str:
        """Extract text content from a response dict."""
        # OpenAI format
        choices = response.get("choices")
        if choices and isinstance(choices, list) and len(choices) > 0:
            msg = choices[0].get("message", {})
            return msg.get("content", "") or ""
        # Simple content key
        return str(response.get("content", "") or response.get("text", "") or "")

    def _score_accuracy(self, content: str, suggestions: List[str]) -> float:
        """Score response accuracy based on basic heuristics."""
        if not content:
            suggestions.append("Response has no content.")
            return 0.0
        if len(content) < 10:
            suggestions.append("Response is too short to assess accuracy.")
            return 0.3
        # Check for refusals without explanation
        for pat in self._COMPILED_REFUSAL_PATTERNS:
            if pat.search(content) and len(content) < 100:
                suggestions.append("Response appears to be an unexplained refusal.")
                return 0.4
        return 0.85

    def _score_completeness(self, content: str, suggestions: List[str]) -> float:
        """Score completeness based on content length and structure."""
        if not content:
            return 0.0
        length = len(content)
        if length < 10:
            suggestions.append("Response is very short; may be incomplete.")
            return 0.2
        if length < 50:
            return 0.5
        if length < 200:
            return 0.75
        return 0.9

    def _score_safety(self, content: str, suggestions: List[str]) -> float:
        """Score safety by checking for harmful patterns."""
        if not content:
            return 1.0
        for pattern in self._COMPILED_UNSAFE_PATTERNS:
            if pattern.search(content):
                suggestions.append("Response may contain unsafe content.")
                return 0.0
        return 1.0

    def _score_coherence(self, content: str, suggestions: List[str]) -> float:
        """Score structural coherence of the response."""
        if not content:
            return 0.0
        # Check for unbalanced brackets as a proxy for broken structure
        opens = content.count("{") + content.count("[") + content.count("(")
        closes = content.count("}") + content.count("]") + content.count(")")
        if abs(opens - closes) > 5:
            suggestions.append("Response structure may be unbalanced.")
            return 0.6
        return 0.9

    def compress_chain_of_thought(self, cot: str) -> str:
        """Compress a chain-of-thought string by removing filler phrases.

        Strips filler phrases and extracts numbered reasoning steps.
        Returns compressed version <= 50% of original length when possible.

        Args:
            cot: Raw chain-of-thought string.

        Returns:
            Compressed chain-of-thought string.
        """
        if not cot:
            return cot

        # Remove filler phrases
        filler_patterns = [
            r"^(Let me think[,.]?\s*)",
            r"^(Well[,.]?\s*)",
            r"^(So[,.]?\s*)",
            r"^(Okay[,.]?\s*)",
            r"^(Hmm[,.]?\s*)",
            r"^(Alright[,.]?\s*)",
            r"^(Now[,.]?\s*)",
        ]
        lines = cot.split("\n")
        cleaned = []
        for line in lines:
            stripped = line.strip()
            for pat in filler_patterns:
                stripped = re.sub(pat, "", stripped, flags=re.IGNORECASE).strip()
            if stripped:
                cleaned.append(stripped)

        result = "\n".join(cleaned)

        # If still > 50% of original, extract numbered steps
        if len(result) > len(cot) * 0.5:
            numbered = re.findall(
                r"(?:^|\n)\s*(?:\d+[.)]\s+|\*\s+|-\s+)(.+?)(?=\n|$)",
                cot,
                re.MULTILINE,
            )
            if numbered and len("\n".join(numbered)) < len(result):
                result = "\n".join(
                    "{0}. {1}".format(i + 1, step.strip())
                    for i, step in enumerate(numbered)
                )

        return result if result else cot

    def retry_with_critique(
        self,
        chat_fn: Callable,
        messages: List[Dict],
        max_retries: int = 3,
        threshold: float = 0.7,
    ) -> Dict[str, Any]:
        """Call chat_fn and retry with critique if quality is below threshold.

        Args:
            chat_fn: Callable that takes messages list and returns response dict.
            messages: Initial messages list.
            max_retries: Maximum number of retry attempts.
            threshold: Minimum acceptable overall score (0.0-1.0).

        Returns:
            Best response dict across all attempts.
        """
        best_result = None
        best_score = -1.0
        current_messages = list(messages)

        for attempt in range(max_retries):
            try:
                result = chat_fn(current_messages)
            except Exception as e:
                result = {"choices": [{"message": {"content": "Error: {0}".format(e)}}]}

            critique = self.evaluate(result)

            if critique.overall > best_score:
                best_score = critique.overall
                best_result = result

            if critique.overall >= threshold:
                break

            # Build critique message for next attempt
            if attempt < max_retries - 1:
                critique_text = (
                    "Your previous response scored {0:.2f}/1.0. "
                    "Please improve: {1}".format(
                        critique.overall,
                        "; ".join(critique.suggestions) if critique.suggestions
                        else "provide a more complete and accurate answer",
                    )
                )
                current_messages = current_messages + [
                    {"role": "system", "content": critique_text}
                ]

        return best_result if best_result is not None else {}


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

CRITIQUE_ENGINE = CritiqueEngine()
