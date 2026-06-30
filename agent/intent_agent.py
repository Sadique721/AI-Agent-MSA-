"""
agent/intent_agent.py
======================
Intent Detection Agent for MSA AI Agent V5.0.
Classifies user queries into task types using regex patterns.
Upgrades to BERT when enable_bert_intent: true in features.yaml.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("msa.agent.intent")

# ── Intent Taxonomy ───────────────────────────────────────────────────────────
INTENT_TYPES = [
    "CODING", "DEBUGGING", "CODE_REVIEW", "TESTING",
    "RESEARCH", "SUMMARIZATION", "QUESTION_ANSWER",
    "ARCHITECTURE", "MATH", "CREATIVE_WRITING",
    "VISION", "SYSTEM_TASK", "GENERAL_QA", "AUTONOMOUS",
]

# ── Regex-based intent patterns ───────────────────────────────────────────────
_PATTERNS: List[Tuple[str, List[str]]] = [
    ("CODING", [
        r"\b(write|create|build|implement|code|generate|develop|make)\b.*(function|class|script|program|app|api|module|component)",
        r"\b(python|javascript|typescript|java|go|rust|sql|html|css)\b.*\b(code|example|snippet)\b",
        r"\bhow (do i|to) (write|implement|build|create)\b",
    ]),
    ("DEBUGGING", [
        r"\b(debug|fix|error|exception|traceback|bug|crash|broken|not working|failing|issue)\b",
        r"\bwhy (is|does|am|are) .*(not|fail|crash|broken|wrong|error)\b",
        r"\b(TypeError|ValueError|AttributeError|ImportError|SyntaxError|RuntimeError)\b",
    ]),
    ("CODE_REVIEW", [
        r"\b(review|check|audit|inspect|analyse|analyze)\b.*(code|function|class|implementation)",
        r"\bis (this|my) (code|implementation) (good|correct|right|ok|efficient|secure)\b",
    ]),
    ("TESTING", [
        r"\b(write|create|generate|add)\b.*(test|unit test|integration test|mock|pytest|jest)\b",
        r"\bhow (do i|to) test\b",
    ]),
    ("RESEARCH", [
        r"\b(research|explain|what is|describe|overview|introduction to|tell me about|elaborate on)\b",
        r"\b(compare|difference between|vs|versus|pros and cons|advantages|disadvantages)\b",
    ]),
    ("SUMMARIZATION", [
        r"\b(summarize|summary|tldr|tl;dr|condense|shorten|brief|overview of)\b",
        r"\bkey (points|takeaways|highlights|findings)\b",
    ]),
    ("ARCHITECTURE", [
        r"\b(design|architecture|system design|high.?level|structure|diagram|blueprint)\b",
        r"\bhow (should i|to) (structure|design|architect|organize)\b",
    ]),
    ("MATH", [
        r"\b(calculate|compute|solve|equation|formula|mathematics|algebra|calculus|statistics|probability)\b",
        r"\bwhat is \d+",
    ]),
    ("CREATIVE_WRITING", [
        r"\b(write|compose|draft|create)\b.*(story|essay|poem|blog|email|letter|article|content)\b",
    ]),
    ("VISION", [
        r"\b(screenshot|image|picture|photo|visual|screen|ocr|extract text from)\b",
        r"\bwhat (is|do) (in|on) (this|the) (image|screenshot|picture)\b",
    ]),
    ("SYSTEM_TASK", [
        r"\b(run|execute|install|uninstall|download|deploy|start|stop|restart|kill)\b",
        r"\b(open|close|create|delete|move|copy|rename) (file|folder|directory|app)\b",
        r"\b(git|docker|npm|pip|bash|terminal|shell|command)\b",
    ]),
    ("AUTONOMOUS", [
        r"\b(do it automatically|automate|on my behalf|without asking|keep going|continue until|finish the whole)\b",
        r"\b(agent|autonomous|self.?improving|multi.?step)\b",
    ]),
]


class IntentAgent:
    """
    Classifies user queries into task types.
    Uses regex patterns as default; BERT when available.
    """

    def __init__(self, method: str = "regex") -> None:
        self.method = method
        self._bert_classifier = None
        if method == "bert":
            self._load_bert()

    def _load_bert(self) -> None:
        try:
            from transformers import pipeline  # type: ignore
            self._bert_classifier = pipeline(
                "text-classification",
                model="distilbert-base-uncased",
                top_k=3,
            )
            logger.info("BERT intent classifier loaded")
        except Exception as e:
            logger.warning("BERT unavailable, falling back to regex: %s", e)
            self.method = "regex"

    def classify(self, query: str) -> Dict[str, object]:
        """
        Classify the query and return intent metadata.

        Returns:
            {
                "intent": "CODING",
                "confidence": 0.92,
                "method": "regex",
                "secondary_intents": ["DEBUGGING"],
            }
        """
        if self.method == "bert" and self._bert_classifier:
            return self._bert_classify(query)
        return self._regex_classify(query)

    def _regex_classify(self, query: str) -> Dict[str, object]:
        query_lower = query.lower()
        matches: List[Tuple[str, int]] = []

        for intent, patterns in _PATTERNS:
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1
            if score > 0:
                matches.append((intent, score))

        if not matches:
            return {
                "intent": "GENERAL_QA",
                "confidence": 0.5,
                "method": "regex",
                "secondary_intents": [],
            }

        matches.sort(key=lambda x: x[1], reverse=True)
        primary = matches[0][0]
        secondary = [m[0] for m in matches[1:3]]
        confidence = min(0.95, 0.6 + matches[0][1] * 0.1)

        return {
            "intent": primary,
            "confidence": confidence,
            "method": "regex",
            "secondary_intents": secondary,
        }

    def _bert_classify(self, query: str) -> Dict[str, object]:
        try:
            results = self._bert_classifier(query[:512])
            top = results[0][0] if results else {}
            return {
                "intent": top.get("label", "GENERAL_QA").upper(),
                "confidence": top.get("score", 0.5),
                "method": "bert",
                "secondary_intents": [],
            }
        except Exception as e:
            logger.warning("BERT classify failed, using regex: %s", e)
            return self._regex_classify(query)


# ── Module-level singleton ────────────────────────────────────────────────────
_intent_agent: Optional[IntentAgent] = None


def get_intent_agent() -> IntentAgent:
    global _intent_agent
    if _intent_agent is None:
        _intent_agent = IntentAgent(method="regex")
    return _intent_agent
