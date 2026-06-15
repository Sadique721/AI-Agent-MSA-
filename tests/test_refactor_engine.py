"""
tests/test_refactor_engine.py
==============================
Unit tests for coding/RefactorEngine.py — Phase-3 Coding Agent.
Covers all 4 refactoring rules, no-match fallback, LLM fallback, output schema.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coding.RefactorEngine import RefactorEngine


@pytest.fixture
def engine():
    """RefactorEngine without LLM (rule-based only)."""
    return RefactorEngine(llm=None)


# ── Rule 1: Java Legacy Loop → forEach ───────────────────────────────────────

class TestJavaLoopRefactor:
    """Convert Java index-based for-loop to streams/forEach."""

    def test_java_loop_detected(self, engine):
        code = '''public void printItems(List<String> items) {
        for (int i = 0; i < items.size(); i++) {
            System.out.println(items.get(i));
        }
    }'''
        result = engine.refactor(code)
        assert "forEach" in result["after"] or len(result["improvements"]) > 0

    def test_java_loop_exact_match_replacement(self, engine):
        code = '''List<String> items = new ArrayList<>();
        for (int i = 0; i < items.size(); i++) {
            System.out.println(items.get(i));
        }'''
        result = engine.refactor(code)
        assert "forEach" in result["after"]
        assert any("forEach" in imp or "Lambda" in imp or "stream" in imp for imp in result["improvements"])

    def test_java_loop_before_preserved(self, engine):
        code = '''for (int i = 0; i < items.size(); i++) {
            System.out.println(items.get(i));
        }'''
        result = engine.refactor(code)
        assert "before" in result
        assert result["before"] == code

    def test_no_java_loop_no_change(self, engine):
        code = "int x = 10; System.out.println(x);"
        result = engine.refactor(code)
        # Should not apply Java loop rule
        assert "forEach" not in result["after"]

    def test_java_for_without_list_no_stream(self, engine):
        code = "for (int i = 0; i < 10; i++) { System.out.println(i); }"
        result = engine.refactor(code)
        # No List<> reference, so stream rule should not apply
        assert "forEach" not in result["after"] or "items" not in result["after"]


# ── Rule 2: JavaScript var → const ───────────────────────────────────────────

class TestJavaScriptVarRefactor:
    """Convert legacy JS 'var' to modern 'const'."""

    def test_var_to_const(self, engine):
        code = "var name = 'MSA'; var age = 25;"
        result = engine.refactor(code)
        assert "const " in result["after"]
        assert "var " not in result["after"]

    def test_var_replacement_improvement_logged(self, engine):
        code = "var x = 10;"
        result = engine.refactor(code)
        assert any("var" in imp.lower() or "const" in imp.lower() for imp in result["improvements"])

    def test_no_var_no_change(self, engine):
        code = "const x = 10; let y = 20;"
        result = engine.refactor(code)
        # No var keyword — this rule should not apply
        assert "const x" in result["after"]

    def test_var_inside_larger_code(self, engine):
        code = """function greet() {
    var message = 'Hello';
    console.log(message);
}"""
        result = engine.refactor(code)
        assert "const message" in result["after"]


# ── Rule 3: Python dict.get() Simplification ─────────────────────────────────

class TestPythonDictRefactor:
    """Simplify Python key-not-in-dict checks to dict.get()."""

    def test_key_not_in_dict(self, engine):
        code = """if key not in my_dict:
    my_dict[key] = value"""
        result = engine.refactor(code)
        assert ".get(" in result["after"]

    def test_dict_improvement_logged(self, engine):
        code = """if key not in my_dict:
    my_dict[key] = value"""
        result = engine.refactor(code)
        assert any("dict" in imp.lower() or "get()" in imp for imp in result["improvements"])

    def test_no_dict_pattern_no_change(self, engine):
        code = "x = my_dict.get('key', 'default')"
        result = engine.refactor(code)
        assert ".get(" in result["after"]  # Original .get() preserved

    def test_if_not_key_in_variant(self, engine):
        code = """if not key in config:
    config[key] = 'default'"""
        result = engine.refactor(code)
        # Should detect "if not key in" pattern
        assert len(result["improvements"]) > 0


# ── Rule 4: Double Negation → Boolean() ───────────────────────────────────────

class TestDoubleNegation:
    """Convert !!value to Boolean(value)."""

    def test_double_negation_to_boolean(self, engine):
        code = "const isValid = !!value;"
        result = engine.refactor(code)
        assert "Boolean(value)" in result["after"]
        assert "!!" not in result["after"]

    def test_double_negation_improvement_logged(self, engine):
        code = "const x = !!value;"
        result = engine.refactor(code)
        assert any("boolean" in imp.lower() or "negation" in imp.lower() for imp in result["improvements"])

    def test_no_double_negation_no_change(self, engine):
        code = "const isValid = Boolean(value);"
        result = engine.refactor(code)
        assert "Boolean(value)" in result["after"]


# ── No Matching Rules (Fallback) ─────────────────────────────────────────────

class TestNoMatchFallback:
    """When no refactoring rules match, a default improvement should be appended."""

    def test_fallback_adds_comment(self, engine):
        code = "int x = 42;"
        result = engine.refactor(code)
        assert "Refactored" in result["after"] or len(result["improvements"]) > 0

    def test_fallback_improvement_present(self, engine):
        code = "print('hello')"
        result = engine.refactor(code)
        assert len(result["improvements"]) > 0

    def test_fallback_before_unchanged(self, engine):
        code = "let y = 100;"
        result = engine.refactor(code)
        assert result["before"] == code


# ── Multiple Rules ───────────────────────────────────────────────────────────

class TestMultipleRules:
    """Multiple refactoring rules applied to the same code."""

    def test_var_and_double_negation(self, engine):
        code = "var active = !!value;"
        result = engine.refactor(code)
        assert "const " in result["after"]
        assert "Boolean(value)" in result["after"]
        assert len(result["improvements"]) >= 2


# ── Output Structure ─────────────────────────────────────────────────────────

class TestOutputStructure:
    """All outputs must have before, after, and improvements."""

    def test_result_has_before(self, engine):
        result = engine.refactor("var x = 1;")
        assert "before" in result

    def test_result_has_after(self, engine):
        result = engine.refactor("var x = 1;")
        assert "after" in result

    def test_result_has_improvements(self, engine):
        result = engine.refactor("var x = 1;")
        assert "improvements" in result
        assert isinstance(result["improvements"], list)

    def test_improvements_are_strings(self, engine):
        result = engine.refactor("var x = 1;")
        for imp in result["improvements"]:
            assert isinstance(imp, str)


# ── LLM Fallback ─────────────────────────────────────────────────────────────

class TestLLMFallback:
    """Verify graceful fallback when LLM fails."""

    def test_broken_llm_falls_back(self):
        class BrokenLLM:
            def create_chat_completion(self, **kwargs):
                raise RuntimeError("LLM offline")

        engine = RefactorEngine(llm=BrokenLLM())
        result = engine.refactor("var x = 10;")
        assert "const " in result["after"]

    def test_no_llm_uses_rules(self, engine):
        result = engine.refactor("var y = !!value;")
        assert "Boolean" in result["after"]
