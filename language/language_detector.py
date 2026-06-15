"""
language/language_detector.py
==============================
Detects whether user input is English, Hindi, or Hinglish.

Strategy:
  1. Check for Devanagari script characters → Hindi
  2. Use langdetect statistical model → English or Hindi
  3. Heuristic: Hindi/Hinglish keywords in Roman script → Hinglish
  4. Fallback → English

Returns:
    {
        "language":   "english" | "hindi" | "hinglish",
        "confidence": float (0.0–1.0),
        "script":     "roman" | "devanagari" | "mixed"
    }
"""

import logging
import re
from typing import Dict

logger = logging.getLogger("msa.language.detector")

# ── Devanagari Unicode range ──────────────────────────────────────────────────
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

# ── Common Hinglish/Hindi Roman-script trigger words ─────────────────────────
# These words appear frequently in Hinglish but rarely in pure English.
_HINGLISH_MARKERS = {
    # Verbs
    "karo", "karna", "kar", "karo", "karta", "karti", "karein",
    "kholo", "khol", "kholdo", "kholna",
    "band", "bando", "bandkaro",
    "chalo", "chala", "chalao",
    "batao", "bata", "batana",
    "dhundo", "dhundho", "khojo",
    "lao", "lana", "leke",
    "dedo", "dena", "do",
    "suno", "sunna", "sunn",
    "dekho", "dekhna", "dekh",
    "jao", "jana", "ja",
    "ruko", "rukna", "ruk",
    "uthao", "uthana",
    "lagao", "laga",
    "hatao", "hata",
    "chhodo", "chhod",
    "shuru", "shurukaro",
    "seedha", "sidha",
    "abhi", "jaldi",
    "phir", "aur",
    "mujhe", "mera", "meri", "mere",
    "hamara", "hamari",
    "tumhara", "apna",
    "kya", "kaun", "kahan", "kaise", "kyun", "kitna",
    "haan", "nahi", "theek", "accha", "sahi",
    "yaar", "bhai", "dost",
    "matlab", "samjha", "samjho",
    "seedha",
    "zara", "thoda",
}

_ENGLISH_STOPWORDS = {
    "open", "close", "start", "run", "please", "search", "find", "google",
    "the", "a", "is", "for", "on", "and", "or", "in", "to", "of", "with",
    "my", "about", "me", "show", "what", "time", "where", "am", "i"
}


# ── Confidence weights ────────────────────────────────────────────────────────
_DEVANAGARI_CONFIDENCE = 0.97
_HINGLISH_MARKER_BASE  = 0.80
_LANGDETECT_WEIGHT     = 0.70


class LanguageDetector:
    """
    Detects language of user input.

    Example:
        detector = LanguageDetector()
        result = detector.detect("Chrome kholo")
        # → {"language": "hinglish", "confidence": 0.85, "script": "roman"}
    """

    def __init__(self):
        self._langdetect_available = self._check_langdetect()
        logger.info(
            "LanguageDetector ready (langdetect=%s)", self._langdetect_available
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _check_langdetect(self) -> bool:
        try:
            from langdetect import detect  # noqa: F401
            return True
        except ImportError:
            logger.warning(
                "langdetect not installed. Using heuristic-only detection. "
                "Run: pip install langdetect"
            )
            return False

    def _has_devanagari(self, text: str) -> bool:
        return bool(_DEVANAGARI_RE.search(text))

    def _hinglish_marker_count(self, text: str) -> int:
        tokens = re.split(r"[\s,\.!?]+", text.lower())
        return sum(1 for t in tokens if t in _HINGLISH_MARKERS)

    def _langdetect_language(self, text: str) -> str:
        """Returns ISO 639-1 code via langdetect, or 'en' on failure."""
        try:
            from langdetect import detect, LangDetectException
            return detect(text)
        except Exception:
            return "en"

    # ── Public API ────────────────────────────────────────────────────────────

    def detect(self, text: str) -> Dict:
        """
        Detect language of input text.

        Args:
            text: Raw user utterance.

        Returns:
            dict with keys: language, confidence, script
        """
        if not text or not text.strip():
            return {"language": "english", "confidence": 1.0, "script": "roman"}

        text = text.strip()

        # ── Step 1: Devanagari script → pure Hindi ────────────────────────────
        if self._has_devanagari(text):
            return {
                "language":   "hindi",
                "confidence": _DEVANAGARI_CONFIDENCE,
                "script":     "devanagari",
            }

        # ── Step 2: Hinglish Roman markers ───────────────────────────────────
        marker_count = self._hinglish_marker_count(text)
        tokens = re.split(r"[\s,\.!?]+", text.lower())
        marker_ratio = marker_count / max(len(tokens), 1)

        if marker_count >= 1:
            confidence = min(_HINGLISH_MARKER_BASE + marker_ratio * 0.15, 0.97)
            return {
                "language":   "hinglish",
                "confidence": round(confidence, 2),
                "script":     "roman",
            }

        # ── Step 3: langdetect ────────────────────────────────────────────────
        if self._langdetect_available:
            lang_code = self._langdetect_language(text)
            if lang_code == "hi":
                # Prevent false positives on short English queries containing English stopwords
                tokens = re.split(r"[\s,\.!?]+", text.lower())
                has_english_word = any(t in _ENGLISH_STOPWORDS for t in tokens)
                if has_english_word and marker_count == 0:
                    pass  # Fall through to English default
                else:
                    return {
                        "language":   "hinglish",  # Roman Hindi = Hinglish
                        "confidence": _LANGDETECT_WEIGHT,
                        "script":     "roman",
                    }

        # ── Step 4: Default → English ─────────────────────────────────────────
        return {
            "language":   "english",
            "confidence": 0.85,
            "script":     "roman",
        }
