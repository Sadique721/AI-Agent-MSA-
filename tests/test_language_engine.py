"""
tests/test_language_engine.py
==============================
Unit tests for the Hinglish Language Engine.
Tests language detection, intent normalization, and response template formatting.
"""

import pytest
from language.language_manager import LanguageManager


def test_language_detection():
    lm = LanguageManager()

    # Test English
    res_en = lm.process("Open Chrome please")
    assert res_en["language"] == "english"

    # Test Hinglish
    res_hing = lm.process("Chrome kholo")
    assert res_hing["language"] == "hinglish"


def test_intent_normalization():
    lm = LanguageManager()

    # App open synonym mapping
    res = lm.process("Notepad start karo")
    assert res["intent"] == "open_app"
    assert res["app"] == "notepad"

    # Search synonym mapping
    res_search = lm.process("search python coding tips")
    assert res_search["intent"] == "internet_search"
    assert "python coding tips" in res_search["query"]


def test_prompt_formatting():
    lm = LanguageManager()

    # Hinglish response formatting check
    res_hing = lm.process("Chrome kholo")
    assert "open kar raha hoon" in res_hing["response"].lower() or "opening" in res_hing["response"].lower()
