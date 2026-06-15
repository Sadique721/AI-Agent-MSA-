"""
tests/test_bug_analyzer.py
===========================
Unit tests for coding/BugAnalyzer.py — Phase-3 Coding Agent.
Covers all rule-based error patterns, LLM fallback, severity, and edge cases.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coding.BugAnalyzer import BugAnalyzer


@pytest.fixture
def analyzer():
    """BugAnalyzer without LLM (rule-based only)."""
    return BugAnalyzer(llm=None)


# ── NullPointerException ─────────────────────────────────────────────────────

class TestNullPointerException:
    """NullPointerException / NPE detection rules."""

    def test_java_npe_detected(self, analyzer):
        result = analyzer.analyze("java.lang.NullPointerException at com.example.Service.run(Service.java:42)")
        assert result["severity"] == "HIGH"
        assert "null" in result["root_cause"].lower()

    def test_npe_shorthand(self, analyzer):
        result = analyzer.analyze("NPE thrown in method getUser()")
        assert result["severity"] == "HIGH"

    def test_js_null_property(self, analyzer):
        result = analyzer.analyze("TypeError: Cannot read properties of null (reading 'name')")
        assert result["severity"] == "HIGH"
        assert "null" in result["root_cause"].lower()

    def test_object_is_null(self, analyzer):
        result = analyzer.analyze("System.NullReferenceException: Object is null")
        assert result["severity"] == "HIGH"

    def test_npe_fix_suggests_null_check(self, analyzer):
        result = analyzer.analyze("NullPointerException")
        assert "null" in result["fix"].lower()


# ── ClassNotFoundException ────────────────────────────────────────────────────

class TestClassNotFound:
    """ClassNotFoundException / NoClassDefFoundError detection."""

    def test_classnotfound_detected(self, analyzer):
        result = analyzer.analyze("java.lang.ClassNotFoundException: com.example.MissingService")
        assert result["severity"] == "HIGH"
        assert "class" in result["root_cause"].lower()

    def test_noclassdeffounderror(self, analyzer):
        result = analyzer.analyze("java.lang.NoClassDefFoundError: org/apache/commons/Util")
        assert result["severity"] == "HIGH"

    def test_classnotfound_fix_suggests_dependency(self, analyzer):
        result = analyzer.analyze("ClassNotFoundException: com.google.gson.Gson")
        assert "dependency" in result["fix"].lower() or "pom" in result["fix"].lower() or "classpath" in result["fix"].lower()


# ── BeanCreationException ────────────────────────────────────────────────────

class TestBeanCreationException:
    """Spring BeanCreationException / UnsatisfiedDependencyException."""

    def test_beancreation_detected(self, analyzer):
        result = analyzer.analyze("org.springframework.beans.factory.BeanCreationException: Error creating bean 'userService'")
        assert result["severity"] == "CRITICAL"

    def test_unsatisfied_dependency(self, analyzer):
        result = analyzer.analyze("UnsatisfiedDependencyException: Error creating bean")
        assert result["severity"] == "CRITICAL"

    def test_could_not_autowire(self, analyzer):
        result = analyzer.analyze("Could not autowire field: private UserRepository")
        assert result["severity"] == "CRITICAL"

    def test_bean_fix_suggests_annotation(self, analyzer):
        result = analyzer.analyze("BeanCreationException in userService")
        assert "@" in result["fix"] or "annotation" in result["fix"].lower() or "component" in result["fix"].lower()


# ── HibernateException / SQL Exceptions ───────────────────────────────────────

class TestDatabaseExceptions:
    """Database / ORM exception detection."""

    def test_hibernate_exception(self, analyzer):
        result = analyzer.analyze("org.hibernate.HibernateException: Could not execute query")
        assert result["severity"] == "HIGH"
        assert "database" in result["root_cause"].lower() or "orm" in result["root_cause"].lower()

    def test_psql_exception(self, analyzer):
        result = analyzer.analyze("org.postgresql.util.PSQLException: Connection refused")
        assert result["severity"] == "HIGH"

    def test_mysql_exception(self, analyzer):
        result = analyzer.analyze("com.mysql.cj.jdbc.exceptions.MySQLServerException: Access denied")
        assert result["severity"] == "HIGH"

    def test_sqlstate_detected(self, analyzer):
        result = analyzer.analyze("ERROR: SQLSTATE[42000]: Syntax error in SQL query")
        assert result["severity"] == "HIGH"

    def test_db_fix_suggests_config(self, analyzer):
        result = analyzer.analyze("HibernateException: table not found")
        assert "properties" in result["fix"].lower() or "schema" in result["fix"].lower() or "connection" in result["fix"].lower()


# ── Angular Dependency Injection ──────────────────────────────────────────────

class TestAngularErrors:
    """Angular InjectorError / DI failures."""

    def test_injector_error(self, analyzer):
        result = analyzer.analyze("InjectorError: No provider for HttpClient")
        assert result["severity"] == "MEDIUM"
        assert "dependency" in result["root_cause"].lower() or "provider" in result["root_cause"].lower()

    def test_no_provider_for(self, analyzer):
        result = analyzer.analyze("No provider for Router in AppComponent")
        assert result["severity"] == "MEDIUM"

    def test_angular_dependency_text(self, analyzer):
        result = analyzer.analyze("Angular dependency injection failure: missing service")
        assert result["severity"] == "MEDIUM"

    def test_angular_fix_suggests_providers(self, analyzer):
        result = analyzer.analyze("No provider for AuthService")
        assert "provider" in result["fix"].lower() or "module" in result["fix"].lower()


# ── JavaScript Runtime Errors ─────────────────────────────────────────────────

class TestJavaScriptErrors:
    """JS TypeError / ReferenceError detection."""

    def test_typeerror_detected(self, analyzer):
        result = analyzer.analyze("TypeError: Cannot call method 'push' of undefined")
        assert result["severity"] == "MEDIUM"

    def test_referenceerror_detected(self, analyzer):
        result = analyzer.analyze("ReferenceError: myVar is not defined")
        assert result["severity"] == "MEDIUM"

    def test_is_not_a_function(self, analyzer):
        result = analyzer.analyze("callback is not a function")
        assert result["severity"] == "MEDIUM"

    def test_js_fix_suggests_scoping(self, analyzer):
        result = analyzer.analyze("ReferenceError: x is not defined")
        assert "let" in result["fix"].lower() or "const" in result["fix"].lower() or "variable" in result["fix"].lower() or "scope" in result["fix"].lower()


# ── Generic Fallback ─────────────────────────────────────────────────────────

class TestGenericFallback:
    """Unrecognized errors should still return a valid result."""

    def test_unknown_error_returns_medium(self, analyzer):
        result = analyzer.analyze("Some completely unknown error happened xyz123")
        assert result["severity"] == "MEDIUM"

    def test_unknown_error_has_all_keys(self, analyzer):
        result = analyzer.analyze("Random error text")
        assert "root_cause" in result
        assert "severity" in result
        assert "fix" in result

    def test_empty_string_returns_generic(self, analyzer):
        result = analyzer.analyze("")
        assert result["severity"] == "MEDIUM"


# ── Output Structure ─────────────────────────────────────────────────────────

class TestOutputStructure:
    """All outputs must have root_cause, severity, and fix."""

    def test_npe_has_all_keys(self, analyzer):
        result = analyzer.analyze("NullPointerException")
        assert set(result.keys()) >= {"root_cause", "severity", "fix"}

    def test_severity_is_valid_value(self, analyzer):
        result = analyzer.analyze("BeanCreationException")
        assert result["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_fix_is_non_empty(self, analyzer):
        result = analyzer.analyze("ClassNotFoundException")
        assert len(result["fix"]) > 5


# ── LLM Fallback ─────────────────────────────────────────────────────────────

class TestLLMFallback:
    """Verify graceful fallback when LLM fails."""

    def test_broken_llm_falls_back(self):
        class BrokenLLM:
            def create_chat_completion(self, **kwargs):
                raise RuntimeError("LLM offline")

        analyzer = BugAnalyzer(llm=BrokenLLM())
        result = analyzer.analyze("NullPointerException at Service.java:10")
        assert result["severity"] == "HIGH"

    def test_no_llm_uses_rules(self, analyzer):
        result = analyzer.analyze("BeanCreationException in Spring context")
        assert result["severity"] == "CRITICAL"
