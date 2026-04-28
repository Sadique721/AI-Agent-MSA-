"""
agent/AgentUtils.py
===================
Shared utilities for the MSA Agent layer.

Provides:
  - setup_logger(name)      → configured logging.Logger
  - parse_intent(text)      → intent label string
  - extract_keywords(text)  → list[str]
  - format_response(...)    → standardised dict payload
"""

import logging
import re
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Logger Factory
# ---------------------------------------------------------------------------

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Return (or create) a named logger with a consistent format.

    Args:
        name:  Logger name, e.g. "msa.agent.service"
        level: Logging level (default: INFO)

    Returns:
        logging.Logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers when module is re-imported
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)

    logger.setLevel(level)
    logger.propagate = False  # Prevent double-logging via root logger
    return logger


# ---------------------------------------------------------------------------
# Intent Keywords Mapping
# ---------------------------------------------------------------------------

_INTENT_MAP: Dict[str, List[str]] = {
    "open_app":          ["open", "launch", "start", "run", "execute"],
    "internet_search":   ["search", "find", "lookup", "google", "browse", "what is", "who is", "how to"],
    "shutdown":          ["shutdown", "shut down", "power off", "turn off"],
    "restart":           ["restart", "reboot", "reset"],
    "mobile_make_call":  ["call", "dial", "ring", "phone"],
    "mobile_set_alarm":  ["alarm", "remind", "reminder", "wake me"],
    "mobile_open_app":   ["mobile open", "phone open", "android open"],
    "automation":        ["automate", "click", "type", "press", "scroll", "move mouse"],
    "vision":            ["capture", "screenshot", "see", "vision", "look", "camera", "detect"],
    "location":          ["location", "where am i", "gps", "navigate", "map"],
    "none":              [],
}

_logger = setup_logger("msa.agent.utils")


# ---------------------------------------------------------------------------
# Intent Parser
# ---------------------------------------------------------------------------

def parse_intent(text: str) -> str:
    """
    Parse the dominant intent from a user command string.

    Uses a simple keyword-matching heuristic over `_INTENT_MAP`.
    Returns one of the action strings defined in the map, or "none".

    Args:
        text: Raw user command / utterance.

    Returns:
        Intent label string (e.g. "open_app", "internet_search", …).
    """
    if not text or not text.strip():
        return "none"

    lower = text.lower().strip()

    for intent, keywords in _INTENT_MAP.items():
        if intent == "none":
            continue
        for kw in keywords:
            # Whole-word match to avoid false positives
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, lower):
                _logger.debug("Intent matched: %r → %s", kw, intent)
                return intent

    _logger.debug("No intent matched for: %r — returning 'none'", text)
    return "none"


# ---------------------------------------------------------------------------
# Keyword Extractor
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "for",
    "of", "and", "or", "but", "not", "with", "this", "that", "my",
    "me", "i", "do", "can", "you", "please", "hey", "msa", "ok",
    "just", "now", "by", "from", "up", "down",
})


def extract_keywords(text: str, max_keywords: int = 8) -> List[str]:
    """
    Extract meaningful keywords from a user command.

    Strips stop-words and short tokens, returns unique tokens preserving order.

    Args:
        text:         Raw command string.
        max_keywords: Maximum number of keywords to return.

    Returns:
        List of keyword strings.
    """
    if not text:
        return []

    # Tokenise — split on whitespace + common punctuation
    tokens = re.split(r"[\s,;!?.'\-\"]+", text.lower())

    seen: set = set()
    keywords: List[str] = []
    for token in tokens:
        token = token.strip()
        if len(token) < 2:
            continue
        if token in _STOP_WORDS:
            continue
        if token not in seen:
            seen.add(token)
            keywords.append(token)
        if len(keywords) >= max_keywords:
            break

    _logger.debug("Keywords for %r: %s", text, keywords)
    return keywords


# ---------------------------------------------------------------------------
# Response Formatter
# ---------------------------------------------------------------------------

def format_response(
    response: str,
    action: str = "none",
    parameters: Optional[Dict[str, Any]] = None,
    status: str = "success",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a standardised JSON-serialisable response payload.

    Args:
        response:   Human-readable reply text.
        action:     Action key (e.g. "open_app", "none").
        parameters: Action parameters dict.
        status:     "success" | "error" | "degraded".
        extra:      Optional additional fields to merge into the payload.

    Returns:
        Dict ready for jsonify() / SocketIO emit().
    """
    payload: Dict[str, Any] = {
        "status":     status,
        "response":   response,
        "action":     action,
        "parameters": parameters or {},
    }
    if extra:
        payload.update(extra)

    return payload
