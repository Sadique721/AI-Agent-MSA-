"""
language/intent_normalizer.py
==============================
Normalizes Hinglish / Hindi / English commands into canonical intent dicts.

Synonym dictionaries map any variant of a command to a standard action.
The normalizer strips trigger verbs to extract the target app/query/contact.

Output format:
    {
        "intent":     str,   # e.g. "open_app", "internet_search", "shutdown"
        "app":        str,   # if intent=open_app (e.g. "chrome")
        "query":      str,   # if intent=internet_search
        "number":     str,   # if intent=mobile_make_call
        "time":       str,   # if intent=mobile_set_alarm
        "raw":        str,   # original normalized text
    }

Example:
    normalizer = IntentNormalizer()
    normalizer.normalize("Chrome kholo")
    # → {"intent": "open_app", "app": "chrome", "raw": "chrome kholo"}
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("msa.language.normalizer")


# ═══════════════════════════════════════════════════════════════════════════════
# Synonym Dictionaries
# Each entry: (canonical_action, [synonym_phrases...])
# Phrases are matched as whole-word patterns (case-insensitive).
# ═══════════════════════════════════════════════════════════════════════════════

# ── Action verb synonyms ──────────────────────────────────────────────────────
_OPEN_SYNONYMS = [
    "kholo", "khol do", "kholdo", "open karo", "open kar",
    "launch karo", "launch kar", "start karo", "start kar",
    "chala do", "chalao", "shuru karo", "shuru kar",
    "run karo", "run kar", "execute karo",
    "open", "launch", "start", "run",
]

_CLOSE_SYNONYMS = [
    "band karo", "band kar", "band kardo", "band kar do",
    "close karo", "close kar", "exit karo", "exit kar",
    "bund karo", "bund kar", "hatao", "hata do",
    "close", "exit", "quit",
]

_SHUTDOWN_SYNONYMS = [
    "shutdown karo", "shutdown kar", "shut down karo",
    "pc band karo", "pc band kar", "pc band kar do",
    "system off karo", "system band karo", "system band kar",
    "computer band karo", "laptop band karo",
    "band kar do", "power off karo",
    "shutdown", "shut down", "power off",
]

_RESTART_SYNONYMS = [
    "restart karo", "restart kar", "reboot karo", "reboot kar",
    "dobara chalu karo", "phir se chalu karo", "reset karo",
    "restart", "reboot", "reset",
]

_SEARCH_SYNONYMS = [
    "search karo", "search kar", "dhundo", "dhundho",
    "khojo", "khoj", "batao", "bata do",
    "google karo", "google kar", "browse karo",
    "pata karo", "pta karo", "jankari do",
    "search", "find", "lookup", "google", "browse",
]

_CALL_SYNONYMS = [
    "call karo", "call kar", "phone karo", "phone kar",
    "dial karo", "dial kar", "baat karo", "baat kar",
    "ring karo", "ring kar", "call kar do",
    "call", "dial", "phone", "ring",
]

_ALARM_SYNONYMS = [
    "alarm laga do", "alarm lagao", "alarm set karo", "alarm set kar",
    "alarm laga", "alarm do", "uthana hai", "reminder set karo",
    "yaad dilao", "remind karo", "remind kar",
    "alarm", "reminder", "remind",
]

_REMEMBER_SYNONYMS = [
    "yaad rakh", "yaad rakho", "remember karo", "save kar",
    "save karo", "note kar", "note karo", "record kar",
    "store kar", "store karo", "remember",
]

_RECALL_SYNONYMS = [
    "yaad hai", "yaad hai kya", "batao mujhe", "kya yaad hai",
    "mujhe batao", "bata", "recall karo", "kya tha",
    "do you remember", "recall",
]

_TIME_SYNONYMS = [
    "time kya hai", "kitne baje hain", "kitne baje hai",
    "waqt kya hai", "abhi kitne baje", "time batao",
    "what time", "current time", "time now",
]

_VISION_SYNONYMS = [
    "screenshot lo", "screenshot lao", "dekho", "capture karo",
    "camera kholo", "photo lo", "photo lao",
    "screenshot", "capture", "camera", "photo",
]

_LOCATION_SYNONYMS = [
    "location batao", "kahan hoon", "meri location", "gps on karo",
    "location", "where am i", "gps",
]

_PROFILE_SYNONYMS = [
    "mera profile", "mere baare mein", "meri info", "mera details",
    "kaun hoon main", "my profile", "about me", "my info",
]

# ── App name aliases (Hinglish → canonical app name) ─────────────────────────
_APP_ALIASES: Dict[str, str] = {
    "chrome":       "chrome",
    "google chrome":"chrome",
    "browser":      "chrome",
    "internet":     "chrome",
    "notepad":      "notepad",
    "note pad":     "notepad",
    "calculator":   "calculator",
    "calc":         "calculator",
    "calci":        "calculator",
    "vs code":      "vs code",
    "vscode":       "vs code",
    "code":         "vs code",
    "visual studio":"vs code",
    "explorer":     "explorer",
    "file manager": "explorer",
    "files":        "explorer",
    "settings":     "settings",
    "setting":      "settings",
    "cmd":          "cmd",
    "command prompt":"cmd",
    "terminal":     "cmd",
    "edge":         "edge",
    "microsoft edge":"edge",
    "word":         "word",
    "ms word":      "word",
    "excel":        "excel",
    "ms excel":     "excel",
    "powerpoint":   "powerpoint",
    "paint":        "paint",
    "task manager": "taskmgr",
    "whatsapp":     "whatsapp",
    "youtube":      "youtube",
    "linkedin":     "linkedin",
    "gmail":        "gmail",
    "spotify":      "spotify",
    "vlc":          "vlc",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Intent Rule Table
# Each rule: (action_name, synonym_list)
# ═══════════════════════════════════════════════════════════════════════════════
_INTENT_RULES: List[Tuple[str, List[str]]] = [
    ("shutdown",          _SHUTDOWN_SYNONYMS),
    ("restart",           _RESTART_SYNONYMS),
    ("mobile_make_call",  _CALL_SYNONYMS),
    ("mobile_set_alarm",  _ALARM_SYNONYMS),
    ("memory_remember",   _REMEMBER_SYNONYMS),
    ("memory_recall",     _RECALL_SYNONYMS),
    ("get_time",          _TIME_SYNONYMS),
    ("vision",            _VISION_SYNONYMS),
    ("location",          _LOCATION_SYNONYMS),
    ("get_profile",       _PROFILE_SYNONYMS),
    ("internet_search",   _SEARCH_SYNONYMS),
    ("open_app",          _OPEN_SYNONYMS),  # open_app LAST (broad match)
    ("close_app",         _CLOSE_SYNONYMS),
]


def _build_pattern(synonym: str) -> re.Pattern:
    """Compile a whole-word, case-insensitive regex for a synonym phrase."""
    escaped = re.escape(synonym.strip())
    return re.compile(r"\b" + escaped + r"\b", re.IGNORECASE)


# Pre-compile all patterns at import time for speed
_COMPILED_RULES: List[Tuple[str, List[re.Pattern]]] = [
    (action, [_build_pattern(s) for s in synonyms])
    for action, synonyms in _INTENT_RULES
]


def _resolve_app(text: str) -> str:
    """Find the best matching app name from text."""
    lower = text.lower()
    # Try longest match first
    for alias in sorted(_APP_ALIASES.keys(), key=len, reverse=True):
        if alias in lower:
            return _APP_ALIASES[alias]
    # Fallback: first token that isn't a stop word
    tokens = re.split(r"[\s,\.!?]+", lower)
    stop = {
        "kholo", "khol", "open", "launch", "start", "karo", "kar",
        "do", "please", "zara", "abhi", "jaldi", "mujhe",
    }
    for t in tokens:
        if t and t not in stop and len(t) > 1:
            return t
    return "app"


def _strip_action_verbs(text: str, synonyms: List[str]) -> str:
    """Remove matched action verb synonyms to reveal the target noun."""
    result = text
    for syn in sorted(synonyms, key=len, reverse=True):
        result = re.sub(r"\b" + re.escape(syn) + r"\b", "", result, flags=re.IGNORECASE)
    return result.strip(" ,.")


class IntentNormalizer:
    """
    Normalizes natural language commands (English / Hindi / Hinglish)
    into canonical intent dicts.

    Example:
        n = IntentNormalizer()
        n.normalize("VS Code khol do")
        # → {"intent": "open_app", "app": "vs code", "raw": "VS Code khol do"}
    """

    def normalize(self, text: str) -> Dict:
        """
        Parse text and return a structured intent dict.

        Args:
            text: Raw user command.

        Returns:
            dict with keys: intent, raw, and intent-specific keys.
        """
        if not text or not text.strip():
            return {"intent": "none", "raw": text}

        stripped = text.strip()

        for action, patterns in _COMPILED_RULES:
            for pattern in patterns:
                if pattern.search(stripped):
                    result = self._build_result(action, stripped, patterns)
                    logger.debug(
                        "Intent matched: %r → %s | result=%s", text, action, result
                    )
                    return result

        # No match — conversational
        logger.debug("No intent matched for: %r", text)
        return {"intent": "none", "raw": stripped, "query": stripped}

    def _build_result(
        self, action: str, text: str, patterns: List[re.Pattern]
    ) -> Dict:
        """Build the full result dict for a matched action."""
        base = {"intent": action, "raw": text}

        if action == "open_app":
            remaining = text
            for p in patterns:
                remaining = p.sub("", remaining)
            app = _resolve_app(remaining) if remaining.strip() else _resolve_app(text)
            base["app"] = app

        elif action == "close_app":
            remaining = text
            for p in patterns:
                remaining = p.sub("", remaining)
            app = _resolve_app(remaining) if remaining.strip() else "current"
            base["app"] = app

        elif action == "internet_search":
            remaining = text
            for p in patterns:
                remaining = p.sub("", remaining)
            base["query"] = remaining.strip(" ,.") or text

        elif action == "mobile_make_call":
            # Extract numbers from text
            nums = re.findall(r"\d+", text)
            base["number"] = nums[0] if nums else ""

        elif action == "mobile_set_alarm":
            # Extract time patterns like "7 baje", "7:30", "7 30"
            time_match = re.search(r"(\d{1,2})[\s:](\d{2})", text)
            if time_match:
                base["hour"]   = time_match.group(1)
                base["minute"] = time_match.group(2)
            else:
                nums = re.findall(r"\d+", text)
                base["hour"]   = nums[0] if nums else "7"
                base["minute"] = nums[1] if len(nums) > 1 else "0"

        elif action == "memory_remember":
            remaining = text
            for p in patterns:
                remaining = p.sub("", remaining)
            base["content"] = remaining.strip(" ,.") or text

        elif action in ("memory_recall", "internet_search"):
            remaining = text
            for p in patterns:
                remaining = p.sub("", remaining)
            base["query"] = remaining.strip(" ,.") or text

        return base
