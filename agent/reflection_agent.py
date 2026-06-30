"""
agent/reflection_agent.py
==========================
Self-critique and Response Refinement Agent for MSA AI Agent V5.0.
Evaluates draft responses for accuracy, completeness, clarity, and safety.
Triggers revision when quality score falls below threshold.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Dict, Optional, Tuple

logger = logging.getLogger("msa.agent.reflection")


class ReflectionResult:
    def __init__(
        self,
        overall_score: float,
        scores: Dict[str, float],
        issues: list,
        suggestions: list,
        requires_revision: bool,
        revised_response: Optional[str] = None,
    ) -> None:
        self.overall_score = overall_score
        self.scores = scores
        self.issues = issues
        self.suggestions = suggestions
        self.requires_revision = requires_revision
        self.revised_response = revised_response

    def to_dict(self) -> Dict:
        return {
            "overall_score": self.overall_score,
            "scores": self.scores,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "requires_revision": self.requires_revision,
            "revised_response": self.revised_response,
        }


class ReflectionAgent:
    """
    Evaluates and optionally revises LLM responses.

    Scoring dimensions:
      - accuracy (30%)   : factual correctness
      - completeness (25%): fully addresses the query
      - clarity (20%)    : well-structured, easy to understand
      - safety (15%)     : no harmful/biased content
      - relevance (10%)  : stays on topic

    Uses heuristic scoring when LLM unavailable.
    Uses LLM-based scoring when an LLM caller is provided.
    """

    WEIGHTS = {
        "accuracy": 0.30,
        "completeness": 0.25,
        "clarity": 0.20,
        "safety": 0.15,
        "relevance": 0.10,
    }

    # Patterns that lower safety score
    _HARMFUL_PATTERNS = [
        r"\b(kill|murder|suicide|self.harm)\b",
        r"\b(hack|exploit|inject|bypass|crack)\s+\w+\s+(to|for|and)\s+(steal|damage|destroy)\b",
        r"\b(password|credit.card|ssn|social.security)\b.*(is|are|=)\s*[\w\d]+",
    ]

    # Patterns indicating incomplete responses
    _INCOMPLETE_PATTERNS = [
        r"i (cannot|can't|won't|don't know|don't have)",
        r"as an ai.*i cannot",
        r"\.\.\.$",                # Ends with ellipsis
        r"to be continued",
    ]

    def __init__(
        self,
        min_quality_score: float = 0.70,
        max_revision_rounds: int = 2,
        llm_caller=None,          # Optional callable(prompt) -> str
    ) -> None:
        self.min_quality_score = min_quality_score
        self.max_revision_rounds = max_revision_rounds
        self._llm = llm_caller
        self._revision_count = 0

    def evaluate(self, query: str, response: str, rag_context: str = "") -> ReflectionResult:
        """Heuristic evaluation of a response."""
        scores: Dict[str, float] = {}
        issues = []
        suggestions = []

        # Safety check
        safety_score = 1.0
        for pattern in self._HARMFUL_PATTERNS:
            if re.search(pattern, response, re.IGNORECASE):
                safety_score = 0.0
                issues.append("Response contains potentially harmful content")
                suggestions.append("Remove or rephrase harmful content")
                break
        scores["safety"] = safety_score

        # Completeness check
        completeness = 0.85
        for pattern in self._INCOMPLETE_PATTERNS:
            if re.search(pattern, response, re.IGNORECASE):
                completeness -= 0.25
                issues.append("Response appears incomplete or evasive")
                suggestions.append("Provide a more complete and direct answer")
                break
        word_count = len(response.split())
        if word_count < 10:
            completeness -= 0.3
            issues.append("Response is too short")
        scores["completeness"] = max(0.0, min(1.0, completeness))

        # Clarity check — structural heuristics
        has_structure = bool(
            re.search(r"(#{1,3} |\*\*|\d+\.|[-•])\s", response)
        )
        clarity = 0.75 + (0.15 if has_structure else 0.0)
        if word_count > 2000:
            clarity -= 0.1
            suggestions.append("Consider making the response more concise")
        scores["clarity"] = min(1.0, clarity)

        # Relevance — basic keyword overlap between query and response
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())
        overlap = len(query_words & response_words) / max(1, len(query_words))
        scores["relevance"] = min(1.0, 0.5 + overlap * 0.5)

        # Accuracy — harder to judge heuristically; use RAG context agreement
        accuracy = 0.80
        if rag_context and len(rag_context) > 50:
            rag_words = set(rag_context.lower().split())
            accuracy_overlap = len(response_words & rag_words) / max(1, len(rag_words) * 0.1)
            accuracy = min(1.0, 0.70 + accuracy_overlap * 0.15)
        scores["accuracy"] = accuracy

        # Compute weighted overall score
        overall = sum(scores[dim] * weight for dim, weight in self.WEIGHTS.items())
        requires_revision = overall < self.min_quality_score or scores["safety"] < 1.0

        return ReflectionResult(
            overall_score=round(overall, 3),
            scores={k: round(v, 3) for k, v in scores.items()},
            issues=issues,
            suggestions=suggestions,
            requires_revision=requires_revision,
            revised_response=None,
        )

    def reflect_and_revise(
        self, query: str, response: str, rag_context: str = ""
    ) -> Tuple[str, ReflectionResult]:
        """
        Evaluate the response. If quality is insufficient and an LLM is available,
        request a revised response. Returns (final_response, result).
        """
        self._revision_count = 0

        for _ in range(self.max_revision_rounds):
            result = self.evaluate(query, response, rag_context)
            if not result.requires_revision:
                break
            if self._llm is None or self._revision_count >= self.max_revision_rounds:
                break
            # Ask LLM to revise
            revision_prompt = (
                f"The following response has quality issues:\n\nISSUES:\n"
                + "\n".join(f"- {i}" for i in result.issues)
                + f"\n\nSUGGESTIONS:\n"
                + "\n".join(f"- {s}" for s in result.suggestions)
                + f"\n\nORIGINAL QUERY: {query}\n\nDRAFT RESPONSE:\n{response}"
                + "\n\nPlease provide an improved response that addresses all issues."
            )
            try:
                revised = self._llm(revision_prompt)
                if revised and len(revised.strip()) > 20:
                    response = revised.strip()
                    self._revision_count += 1
            except Exception as e:
                logger.warning("LLM revision failed: %s", e)
                break

        final_result = self.evaluate(query, response, rag_context)
        return response, final_result


# ── Module singleton ──────────────────────────────────────────────────────────
_reflection_agent: Optional[ReflectionAgent] = None


def get_reflection_agent(min_score: float = 0.70, llm_caller=None) -> ReflectionAgent:
    global _reflection_agent
    if _reflection_agent is None:
        _reflection_agent = ReflectionAgent(min_quality_score=min_score, llm_caller=llm_caller)
    return _reflection_agent
