# language/__init__.py
# ====================
# Hinglish / Hindi / English Language Engine package.
#
# Usage:
#   from language.language_manager import LanguageManager
#   lm = LanguageManager()
#   result = lm.process("Chrome kholo")
#   # → {"intent": "open_app", "app": "chrome", "language": "hinglish",
#   #    "normalized": "open chrome", "response": "Chrome open kar raha hoon."}

from language.language_manager import LanguageManager

__all__ = ["LanguageManager"]
