"""
tests/test_stacktrace_analyzer.py
==================================
Unit tests for coding/StackTraceAnalyzer.py — Phase-3 Coding Agent.
Covers Java, Python, JavaScript stack trace parsing, edge cases, fallback.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coding.StackTraceAnalyzer import StackTraceAnalyzer


@pytest.fixture
def analyzer():
    """StackTraceAnalyzer without LLM (regex-based only)."""
    return StackTraceAnalyzer(llm=None)


# ── Java Stack Trace Parsing ──────────────────────────────────────────────────

class TestJavaStackTrace:
    """Java stack trace format: at pkg.Class.method(File.java:NN)."""

    def test_basic_java_trace(self, analyzer):
        trace = "java.lang.NullPointerException\n\tat com.example.CustomerService.findCustomer(CustomerService.java:55)"
        result = analyzer.analyze(trace)
        assert result["file"] == "CustomerService.java"
        assert result["line"] == 55
        assert result["method"] == "findCustomer"
        assert result["class"] == "com.example.CustomerService"

    def test_java_npe_issue(self, analyzer):
        trace = "java.lang.NullPointerException\n\tat com.example.Svc.run(Svc.java:10)"
        result = analyzer.analyze(trace)
        assert "null" in result["issue"]

    def test_java_classnotfound_issue(self, analyzer):
        trace = "java.lang.ClassNotFoundException: com.example.Missing\n\tat java.net.URLClassLoader.findClass(URLClassLoader.java:387)"
        result = analyzer.analyze(trace)
        assert result["file"] == "URLClassLoader.java"
        assert "class" in result["issue"] or "missing" in result["issue"]

    def test_java_multiline_trace_picks_first(self, analyzer):
        trace = """java.lang.RuntimeException: Failed
\tat com.example.App.main(App.java:20)
\tat com.example.Runner.start(Runner.java:45)"""
        result = analyzer.analyze(trace)
        assert result["file"] == "App.java"
        assert result["line"] == 20

    def test_java_inner_class(self, analyzer):
        trace = "\tat com.example.Outer$Inner.process(Outer.java:99)"
        result = analyzer.analyze(trace)
        assert result["file"] == "Outer.java"
        assert result["line"] == 99
        assert "Inner" in result["class"] or "Outer" in result["class"]

    def test_java_npe_suggestion_mentions_method(self, analyzer):
        trace = "NullPointerException\n\tat com.svc.UserService.getUser(UserService.java:30)"
        result = analyzer.analyze(trace)
        assert "getUser" in result["suggestion"]

    def test_java_classnotfound_suggestion(self, analyzer):
        trace = "ClassNotFoundException\n\tat com.svc.Loader.load(Loader.java:12)"
        result = analyzer.analyze(trace)
        assert "dependency" in result["suggestion"].lower() or "classpath" in result["suggestion"].lower() or "library" in result["suggestion"].lower()


# ── Python Stack Trace Parsing ────────────────────────────────────────────────

class TestPythonStackTrace:
    """Python stack trace format: File "file.py", line N, in func."""

    def test_basic_python_trace(self, analyzer):
        trace = 'Traceback (most recent call last):\n  File "customer.py", line 15, in search_customer\n    result = data[key]'
        result = analyzer.analyze(trace)
        assert result["file"] == "customer.py"
        assert result["line"] == 15
        assert result["method"] == "search_customer"

    def test_python_keyerror(self, analyzer):
        trace = 'File "app.py", line 20, in process\nKeyError: \'missing_key\''
        result = analyzer.analyze(trace)
        assert result["file"] == "app.py"
        assert result["line"] == 20
        assert "key" in result["issue"].lower()

    def test_python_indexerror(self, analyzer):
        trace = 'File "data.py", line 8, in fetch\nIndexError: list index out of range'
        result = analyzer.analyze(trace)
        assert result["file"] == "data.py"
        assert result["line"] == 8
        assert "index" in result["issue"].lower()

    def test_python_generic_exception(self, analyzer):
        trace = 'File "service.py", line 42, in handle_request\nValueError: invalid literal'
        result = analyzer.analyze(trace)
        assert result["file"] == "service.py"
        assert result["line"] == 42
        assert result["method"] == "handle_request"

    def test_python_keyerror_suggestion(self, analyzer):
        trace = 'File "utils.py", line 5, in get_value\nKeyError: \'name\''
        result = analyzer.analyze(trace)
        assert ".get()" in result["suggestion"] or "key" in result["suggestion"].lower()

    def test_python_indexerror_suggestion(self, analyzer):
        trace = 'File "list_ops.py", line 12, in process\nIndexError: list index out of range'
        result = analyzer.analyze(trace)
        assert "length" in result["suggestion"].lower() or "index" in result["suggestion"].lower()


# ── JavaScript Stack Trace Parsing ────────────────────────────────────────────

class TestJavaScriptStackTrace:
    """JS stack trace format: at func (file.js:line:col) or at file.js:line:col."""

    def test_basic_js_trace_with_function(self, analyzer):
        trace = "TypeError: Cannot read property 'name'\n    at findCustomer (CustomerService.js:55:12)"
        result = analyzer.analyze(trace)
        assert result["file"] == "CustomerService.js"
        assert result["line"] == 55
        assert result["method"] == "findCustomer"

    def test_js_anonymous_function(self, analyzer):
        trace = "Error: something failed\n    at (app.js:10:5)"
        result = analyzer.analyze(trace)
        assert result["file"] == "app.js"
        assert result["line"] == 10

    def test_js_typeerror_issue(self, analyzer):
        trace = "TypeError: obj.doStuff is not a function\n    at main (index.js:30:8)"
        result = analyzer.analyze(trace)
        assert "type" in result["issue"].lower()

    def test_js_typeerror_suggestion(self, analyzer):
        trace = "TypeError: Cannot read property\n    at render (App.js:100:4)"
        result = analyzer.analyze(trace)
        assert "render" in result["suggestion"] or "object" in result["suggestion"].lower()


# ── Fallback Parsing ─────────────────────────────────────────────────────────

class TestFallbackParsing:
    """Unrecognized formats should return a safe fallback."""

    def test_unknown_format_returns_result(self, analyzer):
        trace = "Some random error text without standard format"
        result = analyzer.analyze(trace)
        assert "file" in result
        assert "line" in result
        assert "issue" in result
        assert "suggestion" in result

    def test_unknown_format_default_file(self, analyzer):
        trace = "Completely unparseable error dump"
        result = analyzer.analyze(trace)
        assert result["file"] == "UnknownSource.java"

    def test_fallback_extracts_line_number(self, analyzer):
        trace = "Error at line 42 in unknown context"
        result = analyzer.analyze(trace)
        assert result["line"] == 42

    def test_fallback_extracts_line_with_colon(self, analyzer):
        trace = "Error occurred :99 somewhere"
        result = analyzer.analyze(trace)
        assert result["line"] == 99

    def test_empty_trace_returns_fallback(self, analyzer):
        result = analyzer.analyze("")
        assert result["file"] == "UnknownSource.java"
        assert result["line"] == 1


# ── Output Structure ─────────────────────────────────────────────────────────

class TestOutputStructure:
    """Verify all outputs have required keys."""

    def test_java_output_has_all_keys(self, analyzer):
        trace = "\tat com.example.Svc.run(Svc.java:10)"
        result = analyzer.analyze(trace)
        assert set(result.keys()) >= {"file", "line", "issue", "suggestion"}

    def test_python_output_has_all_keys(self, analyzer):
        trace = 'File "app.py", line 5, in main'
        result = analyzer.analyze(trace)
        assert set(result.keys()) >= {"file", "line", "issue", "suggestion", "method"}

    def test_line_is_integer(self, analyzer):
        trace = "\tat com.example.Svc.run(Svc.java:10)"
        result = analyzer.analyze(trace)
        assert isinstance(result["line"], int)

    def test_file_is_string(self, analyzer):
        trace = 'File "test.py", line 1, in module'
        result = analyzer.analyze(trace)
        assert isinstance(result["file"], str)


# ── LLM Fallback ─────────────────────────────────────────────────────────────

class TestLLMFallback:
    """Verify graceful fallback when LLM fails."""

    def test_broken_llm_falls_back(self):
        class BrokenLLM:
            def create_chat_completion(self, **kwargs):
                raise RuntimeError("LLM offline")

        analyzer = StackTraceAnalyzer(llm=BrokenLLM())
        result = analyzer.analyze("\tat com.example.App.main(App.java:1)")
        assert result["file"] == "App.java"

    def test_no_llm_uses_regex(self, analyzer):
        trace = 'File "main.py", line 42, in run'
        result = analyzer.analyze(trace)
        assert result["line"] == 42
