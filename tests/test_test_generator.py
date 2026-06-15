"""
tests/test_test_generator.py
==============================
Unit tests for coding/TestGenerator.py — Phase-3 Coding Agent.
Covers JUnit, PyTest, Jest generation, framework auto-detection, LLM fallback.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coding.TestGenerator import TestGenerator


@pytest.fixture
def gen():
    """TestGenerator without LLM (rule-based only)."""
    return TestGenerator(llm=None)


# ── Framework Auto-Detection ─────────────────────────────────────────────────

class TestFrameworkAutoDetection:
    """Verify automatic test framework detection from code content."""

    def test_detect_junit_from_java_class(self, gen):
        code = "public class UserService { public void findUser(String name) {} }"
        result = gen.generate(code)
        assert result["framework"] == "junit5"

    def test_detect_junit_from_void_keyword(self, gen):
        code = "public void process(String data) { return; }"
        result = gen.generate(code)
        assert result["framework"] == "junit5"

    def test_detect_pytest_from_def(self, gen):
        code = "def search_customer(query, customers):\n    return []"
        result = gen.generate(code)
        assert result["framework"] == "pytest"

    def test_detect_jest_from_function(self, gen):
        code = "function findCustomer(name, db) { return db.find(c => c.name === name); }"
        result = gen.generate(code)
        assert result["framework"] == "jest"

    def test_detect_jest_from_const(self, gen):
        code = "const findUser = (id) => users.find(u => u.id === id);"
        result = gen.generate(code)
        assert result["framework"] == "jest"

    def test_default_to_pytest(self, gen):
        code = "# Just a comment, no language markers"
        result = gen.generate(code)
        assert result["framework"] == "pytest"


# ── Explicit Framework Override ───────────────────────────────────────────────

class TestExplicitFramework:
    """Verify explicit framework parameter overrides auto-detection."""

    def test_explicit_junit(self, gen):
        code = "def something(): pass"  # would normally detect pytest
        result = gen.generate(code, framework="junit")
        assert result["framework"] == "junit5"

    def test_explicit_pytest(self, gen):
        code = "public class X { }"  # would normally detect junit
        result = gen.generate(code, framework="pytest")
        assert result["framework"] == "pytest"

    def test_explicit_jest(self, gen):
        code = "def something(): pass"
        result = gen.generate(code, framework="jest")
        assert result["framework"] == "jest"

    def test_explicit_spring(self, gen):
        code = "something"
        result = gen.generate(code, framework="spring")
        assert result["framework"] == "junit5"


# ── JUnit Generation ─────────────────────────────────────────────────────────

class TestJUnitGeneration:
    """Verify JUnit 5 test generation content."""

    def test_junit_has_test_annotation(self, gen):
        result = gen.generate_junit("public class UserService {}")
        assert "@Test" in result["test_code"]

    def test_junit_has_before_each(self, gen):
        result = gen.generate_junit("public class UserService {}")
        assert "@BeforeEach" in result["test_code"]

    def test_junit_has_assertions(self, gen):
        result = gen.generate_junit("public class UserService {}")
        assert "assertNotNull" in result["test_code"] or "assertEquals" in result["test_code"]

    def test_junit_has_positive_case(self, gen):
        result = gen.generate_junit("public class UserService {}")
        assert "PositiveCase" in result["test_code"] or "positive" in result["test_code"].lower()

    def test_junit_has_negative_case(self, gen):
        result = gen.generate_junit("public class UserService {}")
        assert "NegativeCase" in result["test_code"] or "negative" in result["test_code"].lower()

    def test_junit_has_edge_case(self, gen):
        result = gen.generate_junit("public class UserService {}")
        assert "EdgeCase" in result["test_code"] or "edge" in result["test_code"].lower() or "Null" in result["test_code"]

    def test_junit_framework_label(self, gen):
        result = gen.generate_junit("code")
        assert result["framework"] == "junit5"

    def test_junit_explanation_present(self, gen):
        result = gen.generate_junit("code")
        assert "explanation" in result
        assert len(result["explanation"]) > 10


# ── PyTest Generation ────────────────────────────────────────────────────────

class TestPyTestGeneration:
    """Verify PyTest test generation content."""

    def test_pytest_has_test_functions(self, gen):
        result = gen.generate_pytest("def search(): pass")
        assert "def test_" in result["test_code"]

    def test_pytest_has_assert(self, gen):
        result = gen.generate_pytest("def search(): pass")
        assert "assert " in result["test_code"]

    def test_pytest_has_positive_case(self, gen):
        result = gen.generate_pytest("def search(): pass")
        assert "positive" in result["test_code"].lower()

    def test_pytest_has_negative_case(self, gen):
        result = gen.generate_pytest("def search(): pass")
        assert "negative" in result["test_code"].lower() or "nonexistent" in result["test_code"].lower()

    def test_pytest_has_edge_case(self, gen):
        result = gen.generate_pytest("def search(): pass")
        assert "edge" in result["test_code"].lower() or "empty" in result["test_code"].lower()

    def test_pytest_framework_label(self, gen):
        result = gen.generate_pytest("code")
        assert result["framework"] == "pytest"


# ── Jest Generation ──────────────────────────────────────────────────────────

class TestJestGeneration:
    """Verify Jest test generation content."""

    def test_jest_has_describe(self, gen):
        result = gen.generate_jest("function find() {}")
        assert "describe(" in result["test_code"]

    def test_jest_has_test(self, gen):
        result = gen.generate_jest("function find() {}")
        assert "test(" in result["test_code"]

    def test_jest_has_expect(self, gen):
        result = gen.generate_jest("function find() {}")
        assert "expect(" in result["test_code"]

    def test_jest_has_before_each(self, gen):
        result = gen.generate_jest("function find() {}")
        assert "beforeEach" in result["test_code"]

    def test_jest_framework_label(self, gen):
        result = gen.generate_jest("code")
        assert result["framework"] == "jest"

    def test_jest_has_positive_test(self, gen):
        result = gen.generate_jest("function find() {}")
        assert "positive" in result["test_code"].lower() or "locate" in result["test_code"].lower()


# ── Output Structure ─────────────────────────────────────────────────────────

class TestOutputStructure:
    """All outputs must have framework, test_code, and explanation."""

    def test_result_has_framework(self, gen):
        result = gen.generate("def foo(): pass")
        assert "framework" in result

    def test_result_has_test_code(self, gen):
        result = gen.generate("def foo(): pass")
        assert "test_code" in result
        assert len(result["test_code"]) > 20

    def test_result_has_explanation(self, gen):
        result = gen.generate("def foo(): pass")
        assert "explanation" in result
        assert len(result["explanation"]) > 5


# ── LLM Fallback ─────────────────────────────────────────────────────────────

class TestLLMFallback:
    """Verify graceful fallback when LLM fails."""

    def test_broken_llm_falls_back(self):
        class BrokenLLM:
            def create_chat_completion(self, **kwargs):
                raise RuntimeError("LLM offline")

        gen = TestGenerator(llm=BrokenLLM())
        result = gen.generate("def foo(): pass")
        assert result["framework"] == "pytest"

    def test_no_llm_uses_rules(self, gen):
        result = gen.generate("public class X { public void run() {} }")
        assert result["framework"] == "junit5"
