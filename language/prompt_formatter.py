"""
language/prompt_formatter.py
=============================
Generates language-matched responses for the MSA Agent.

The formatter takes an intent + detected language and returns a response
string in the same language as the user's input.

Supported languages: English, Hinglish, Hindi (Roman script)

Example:
    formatter = PromptFormatter()
    formatter.format("open_app", "hinglish", app="VS Code")
    # → "VS Code open kar raha hoon."

    formatter.format("open_app", "english", app="Chrome")
    # → "Opening Chrome for you."
"""

import logging
from typing import Optional

logger = logging.getLogger("msa.language.formatter")


# ═══════════════════════════════════════════════════════════════════════════════
# Response Templates
# Keys: (intent, language) → template string with {placeholders}
# ═══════════════════════════════════════════════════════════════════════════════

_TEMPLATES = {
    # ── open_app ──────────────────────────────────────────────────────────────
    ("open_app", "english"):   "Opening {app} for you.",
    ("open_app", "hinglish"):  "{app} open kar raha hoon.",
    ("open_app", "hindi"):     "{app} khol raha hoon.",

    # ── close_app ─────────────────────────────────────────────────────────────
    ("close_app", "english"):  "Closing {app} now.",
    ("close_app", "hinglish"): "{app} band kar raha hoon.",
    ("close_app", "hindi"):    "{app} band kar raha hoon.",

    # ── shutdown ──────────────────────────────────────────────────────────────
    ("shutdown", "english"):   "Shutting down the system. Goodbye!",
    ("shutdown", "hinglish"):  "System band kar raha hoon. Alvida!",
    ("shutdown", "hindi"):     "System band ho raha hai. Alvida!",

    # ── restart ───────────────────────────────────────────────────────────────
    ("restart", "english"):    "Restarting the system now.",
    ("restart", "hinglish"):   "System restart kar raha hoon.",
    ("restart", "hindi"):      "System dobara shuru ho raha hai.",

    # ── internet_search ───────────────────────────────────────────────────────
    ("internet_search", "english"):   "Searching the web for: {query}",
    ("internet_search", "hinglish"):  "{query} ke baare mein search kar raha hoon.",
    ("internet_search", "hindi"):     "{query} ke liye khoj raha hoon.",

    # ── mobile_make_call ──────────────────────────────────────────────────────
    ("mobile_make_call", "english"):  "Calling {number} on your mobile.",
    ("mobile_make_call", "hinglish"): "{number} pe call kar raha hoon.",
    ("mobile_make_call", "hindi"):    "{number} par call kar raha hoon.",

    # ── mobile_set_alarm ──────────────────────────────────────────────────────
    ("mobile_set_alarm", "english"):  "Setting alarm for {hour}:{minute}.",
    ("mobile_set_alarm", "hinglish"): "{hour}:{minute} baje ka alarm laga raha hoon.",
    ("mobile_set_alarm", "hindi"):    "{hour}:{minute} baje ke liye alarm set kar raha hoon.",

    # ── mobile_open_app ───────────────────────────────────────────────────────
    ("mobile_open_app", "english"):  "Opening {app} on your phone.",
    ("mobile_open_app", "hinglish"): "Phone pe {app} khol raha hoon.",
    ("mobile_open_app", "hindi"):    "Mobile pe {app} khol raha hoon.",

    # ── get_time ──────────────────────────────────────────────────────────────
    ("get_time", "english"):   "The current time is {time}.",
    ("get_time", "hinglish"):  "Abhi {time} baje hain.",
    ("get_time", "hindi"):     "Abhi samay {time} hai.",

    # ── get_profile ───────────────────────────────────────────────────────────
    ("get_profile", "english"):  "Here is your profile: {profile}",
    ("get_profile", "hinglish"): "Aapka profile yeh hai: {profile}",
    ("get_profile", "hindi"):    "Aapki jaankari: {profile}",

    # ── vision ────────────────────────────────────────────────────────────────
    ("vision", "english"):   "Capturing camera frame now.",
    ("vision", "hinglish"):  "Camera se photo le raha hoon.",
    ("vision", "hindi"):     "Camera se tasveer le raha hoon.",

    # ── location ──────────────────────────────────────────────────────────────
    ("location", "english"):  "Fetching your current location.",
    ("location", "hinglish"): "Aapki location dhundh raha hoon.",
    ("location", "hindi"):    "Aapka sthan pata kar raha hoon.",

    # ── memory_remember ───────────────────────────────────────────────────────
    ("memory_remember", "english"):  "Got it! I'll remember that.",
    ("memory_remember", "hinglish"): "Theek hai! Yaad rakhta hoon.",
    ("memory_remember", "hindi"):    "Theek hai! Yaad rakh lunga.",

    # ── memory_recall ─────────────────────────────────────────────────────────
    ("memory_recall", "english"):  "Let me check my memory for: {query}",
    ("memory_recall", "hinglish"): "{query} ke baare mein yaad kar raha hoon.",
    ("memory_recall", "hindi"):    "{query} ke baare mein yad kar raha hoon.",

    # ── browser_search ────────────────────────────────────────────────────────
    ("browser_search", "english"):  "Opening browser and searching for: {query}",
    ("browser_search", "hinglish"): "Browser mein {query} search kar raha hoon.",
    ("browser_search", "hindi"):    "Browser mein {query} khoj raha hoon.",

    # ── none (conversational) ─────────────────────────────────────────────────
    ("none", "english"):   "I received your message. How can I help you?",
    ("none", "hinglish"):  "Aapka message mila. Kaise help karun?",
    ("none", "hindi"):     "Aapka sandesh mila. Kaise madad karun?",

    # ── error fallback ────────────────────────────────────────────────────────
    ("error", "english"):  "Sorry, something went wrong. Please try again.",
    ("error", "hinglish"): "Maafi, kuch galat hua. Phir se try karein.",
    ("error", "hindi"):    "Kshama karein, kuch galat hua. Punah prayaas karein.",
}

# Default language if detection fails
_DEFAULT_LANG = "english"


class PromptFormatter:
    """
    Generates language-matched response strings.

    Usage:
        formatter = PromptFormatter()

        # Hinglish response
        formatter.format("open_app", "hinglish", app="Chrome")
        → "Chrome open kar raha hoon."

        # English response
        formatter.format("internet_search", "english", query="Python tutorials")
        → "Searching the web for: Python tutorials"
    """

    def format(
        self,
        intent: str,
        language: str,
        **kwargs,
    ) -> str:
        """
        Generate a response string matching the user's language.

        Args:
            intent:   The resolved intent (e.g. "open_app", "shutdown").
            language: Detected language ("english", "hinglish", "hindi").
            **kwargs: Template placeholders (e.g. app="Chrome", query="Python").

        Returns:
            Formatted response string.
        """
        lang = language if language in ("english", "hinglish", "hindi") else _DEFAULT_LANG

        # Try exact (intent, lang) match
        template = _TEMPLATES.get((intent, lang))

        # Fallback chain: hinglish → english
        if template is None:
            template = _TEMPLATES.get((intent, "english"))

        # Last resort
        if template is None:
            template = _TEMPLATES.get(("none", lang), "Command received.")

        try:
            response = template.format(**kwargs)
        except KeyError as e:
            logger.warning(
                "PromptFormatter: missing placeholder %s for intent=%s lang=%s",
                e, intent, lang,
            )
            # Return template with unfilled slots stripped
            response = template.split("{")[0].strip() or "Processing your request."

        logger.debug(
            "PromptFormatter: intent=%s lang=%s → %r", intent, lang, response
        )
        return response

    def format_error(self, language: str, detail: str = "") -> str:
        """Return a language-matched error response."""
        lang = language if language in ("english", "hinglish", "hindi") else _DEFAULT_LANG
        base = _TEMPLATES.get(("error", lang), "Something went wrong.")
        return f"{base} ({detail})" if detail else base

    def list_supported_intents(self):
        """Return all intents that have response templates."""
        return sorted({intent for intent, _ in _TEMPLATES.keys()})
