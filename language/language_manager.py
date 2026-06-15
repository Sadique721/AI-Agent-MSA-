"""
language/language_manager.py
==============================
High-level facade for the complete Hinglish / Hindi / English Language Engine.

Integrates:
  - LanguageDetector   → detects language
  - IntentNormalizer   → maps Hinglish/Hindi to canonical intents
  - PromptFormatter    → generates language-matched responses

This is the single entry point all other modules should use.

Usage:
    from language.language_manager import LanguageManager

    lm = LanguageManager()

    # Hinglish input
    result = lm.process("Chrome kholo")
    # {
    #   "intent": "open_app",
    #   "app": "chrome",
    #   "language": "hinglish",
    #   "confidence": 0.85,
    #   "response": "Chrome open kar raha hoon.",
    #   "normalized": {"intent": "open_app", "app": "chrome", "raw": "Chrome kholo"},
    #   "detection": {"language": "hinglish", "confidence": 0.85, "script": "roman"}
    # }

    # English input
    result = lm.process("Open Notepad")
    # {
    #   "intent": "open_app",
    #   "app": "notepad",
    #   "language": "english",
    #   "response": "Opening notepad for you.",
    #   ...
    # }
"""

import logging
from typing import Any, Dict, Optional

from language.language_detector import LanguageDetector
from language.intent_normalizer import IntentNormalizer
from language.prompt_formatter import PromptFormatter

logger = logging.getLogger("msa.language.manager")


class LanguageManager:
    """
    Unified language engine facade.

    Detects language, normalizes intent, generates language-matched response.
    All subsystems are lazily initialized and error-tolerant.
    """

    def __init__(self):
        self._detector   = LanguageDetector()
        self._normalizer = IntentNormalizer()
        self._formatter  = PromptFormatter()
        logger.info("LanguageManager initialized.")

    # ── Primary API ───────────────────────────────────────────────────────────

    def process(self, text: str) -> Dict[str, Any]:
        """
        Full pipeline: text → detect → normalize → format response.

        Args:
            text: Raw user utterance (any language/script).

        Returns:
            dict with keys:
                intent      str    — canonical action label
                language    str    — detected language
                confidence  float  — detection confidence
                response    str    — language-matched response string
                normalized  dict   — full intent normalization output
                detection   dict   — full language detection output
                + intent-specific keys (app, query, number, etc.)
        """
        if not text or not text.strip():
            return self._empty_result()

        # ── Step 1: Language Detection ────────────────────────────────────────
        try:
            detection = self._detector.detect(text)
        except Exception as e:
            logger.error("LanguageDetector error: %s", e)
            detection = {"language": "english", "confidence": 0.5, "script": "roman"}

        language   = detection.get("language", "english")
        confidence = detection.get("confidence", 0.5)

        # ── Step 2: Intent Normalization ──────────────────────────────────────
        try:
            normalized = self._normalizer.normalize(text)
        except Exception as e:
            logger.error("IntentNormalizer error: %s", e)
            normalized = {"intent": "none", "raw": text}

        intent = normalized.get("intent", "none")

        # ── Step 3: Build template kwargs from normalized dict ─────────────────
        kwargs = {k: v for k, v in normalized.items() if k not in ("intent", "raw")}

        # ── Step 4: Format language-matched response ──────────────────────────
        try:
            response = self._formatter.format(intent, language, **kwargs)
        except Exception as e:
            logger.error("PromptFormatter error: %s", e)
            response = self._formatter.format_error(language, str(e))

        # ── Assemble result ───────────────────────────────────────────────────
        result: Dict[str, Any] = {
            "intent":     intent,
            "language":   language,
            "confidence": confidence,
            "response":   response,
            "normalized": normalized,
            "detection":  detection,
        }
        # Bubble up intent-specific keys to top level for easy access
        result.update(kwargs)

        logger.info(
            "LanguageManager: text=%r → lang=%s intent=%s",
            text[:60], language, intent,
        )
        return result

    # ── Convenience helpers ───────────────────────────────────────────────────

    def detect_language(self, text: str) -> str:
        """Return only the detected language string."""
        return self._detector.detect(text).get("language", "english")

    def normalize(self, text: str) -> Dict:
        """Return only the normalized intent dict."""
        return self._normalizer.normalize(text)

    def format_response(self, intent: str, language: str, **kwargs) -> str:
        """Return a formatted response for given intent and language."""
        return self._formatter.format(intent, language, **kwargs)

    def supported_intents(self):
        """List all intents with response templates."""
        return self._formatter.list_supported_intents()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _empty_result(self) -> Dict:
        return {
            "intent":     "none",
            "language":   "english",
            "confidence": 1.0,
            "response":   "Please say or type a command.",
            "normalized": {"intent": "none", "raw": ""},
            "detection":  {"language": "english", "confidence": 1.0, "script": "roman"},
        }
