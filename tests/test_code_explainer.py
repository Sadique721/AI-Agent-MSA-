"""
tests/test_code_explainer.py
==============================
Unit tests for coding/CodeExplainer.py — Phase-3 Coding Agent.
Covers rule-based explanations, language detection, line parsing, LLM fallback.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coding.CodeExplainer import CodeExplainer


@pytest.fixture
def explainer():
    """CodeExplainer without LLM (rule-based only)."""
    return CodeExplainer(llm=None)


# ── High-Level Summary Detection ─────────────────────────────────────────────

class TestSummaryDetection:
    """Verify high-level summary detection based on code content."""

    def test_springboot_application(self, explainer):
        code = "@SpringBootApplication\npublic class Application {}"
        result = explainer.explain(code)
        assert "spring boot" in result["summary"].lower() or "bootstrap" in result["summary"].lower()

    def test_rest_controller(self, explainer):
        code = "@RestController\n@RequestMapping(\"/api\")\npublic class UserController {}"
        result = explainer.explain(code)
        assert "rest" in result["summary"].lower() or "controller" in result["summary"].lower()

    def test_service_class(self, explainer):
        code = "@Service\npublic class UserService { }"
        result = explainer.explain(code)
        assert "service" in result["summary"].lower()

    def test_python_script(self, explainer):
        code = "def search_customer(query):\n    return []"
        result = explainer.explain(code)
        assert "python" in result["summary"].lower()

    def test_generic_code(self, explainer):
        code = "int x = 42;"
        result = explainer.explain(code)
        assert "summary" in result
        assert len(result["summary"]) > 5


# ── Line-by-Line Explanation ──────────────────────────────────────────────────

class TestLineExplanations:
    """Verify individual line explanations."""

    def test_package_statement(self, explainer):
        code = "package com.example.demo;"
        result = explainer.explain(code)
        exps = result["line_explanations"]
        assert len(exps) == 1
        assert "namespace" in exps[0]["explanation"].lower() or "package" in exps[0]["explanation"].lower()

    def test_import_statement(self, explainer):
        code = "import java.util.List;"
        result = explainer.explain(code)
        exps = result["line_explanations"]
        assert "import" in exps[0]["explanation"].lower() or "library" in exps[0]["explanation"].lower() or "load" in exps[0]["explanation"].lower()

    def test_rest_controller_annotation(self, explainer):
        code = "@RestController"
        result = explainer.explain(code)
        exps = result["line_explanations"]
        assert "controller" in exps[0]["explanation"].lower() or "routing" in exps[0]["explanation"].lower()

    def test_autowired_annotation(self, explainer):
        code = "@Autowired\nprivate UserService service;"
        result = explainer.explain(code)
        autowired = [e for e in result["line_explanations"] if "@Autowired" in e["code"]]
        assert len(autowired) == 1
        assert "injection" in autowired[0]["explanation"].lower() or "dependency" in autowired[0]["explanation"].lower()

    def test_class_declaration(self, explainer):
        code = "public class UserService { }"
        result = explainer.explain(code)
        exps = result["line_explanations"]
        class_exps = [e for e in exps if "class" in e["code"].lower()]
        assert len(class_exps) >= 1
        assert "class" in class_exps[0]["explanation"].lower()

    def test_interface_declaration(self, explainer):
        code = "public interface UserRepository { }"
        result = explainer.explain(code)
        exps = result["line_explanations"]
        assert any("contract" in e["explanation"].lower() or "interface" in e["explanation"].lower() for e in exps)

    def test_get_mapping(self, explainer):
        code = '@GetMapping("/users")'
        result = explainer.explain(code)
        exps = result["line_explanations"]
        assert any("get" in e["explanation"].lower() for e in exps)

    def test_post_mapping(self, explainer):
        code = '@PostMapping("/users")'
        result = explainer.explain(code)
        exps = result["line_explanations"]
        assert any("post" in e["explanation"].lower() for e in exps)

    def test_python_def(self, explainer):
        code = "def search_customer(query):\n    return []"
        result = explainer.explain(code)
        def_exps = [e for e in result["line_explanations"] if "def " in e["code"]]
        assert len(def_exps) == 1
        assert "method" in def_exps[0]["explanation"].lower() or "function" in def_exps[0]["explanation"].lower() or "python" in def_exps[0]["explanation"].lower()

    def test_return_statement(self, explainer):
        code = "return results;"
        result = explainer.explain(code)
        exps = result["line_explanations"]
        assert any("return" in e["explanation"].lower() for e in exps)

    def test_assert_statement(self, explainer):
        code = "assert result is not None"
        result = explainer.explain(code)
        exps = result["line_explanations"]
        assert any("assert" in e["explanation"].lower() for e in exps)


# ── Empty Lines Skipped ──────────────────────────────────────────────────────

class TestEmptyLineHandling:
    """Empty lines should be skipped in explanations."""

    def test_empty_lines_skipped(self, explainer):
        code = "import os\n\n\ndef main():\n    pass"
        result = explainer.explain(code)
        # Empty lines should not appear in explanations
        codes = [e["code"].strip() for e in result["line_explanations"]]
        assert "" not in codes

    def test_only_whitespace_skipped(self, explainer):
        code = "   \n\t\nimport os"
        result = explainer.explain(code)
        assert len(result["line_explanations"]) == 1


# ── Line Numbers ─────────────────────────────────────────────────────────────

class TestLineNumbers:
    """Line numbers should be 1-indexed and sequential."""

    def test_line_numbers_start_at_1(self, explainer):
        code = "package com.example;\nimport java.util.List;"
        result = explainer.explain(code)
        assert result["line_explanations"][0]["line"] == 1

    def test_line_numbers_sequential(self, explainer):
        code = "import os\nimport sys\nimport json"
        result = explainer.explain(code)
        lines = [e["line"] for e in result["line_explanations"]]
        assert lines == [1, 2, 3]

    def test_line_numbers_skip_blanks(self, explainer):
        code = "import os\n\nimport sys"
        result = explainer.explain(code)
        lines = [e["line"] for e in result["line_explanations"]]
        assert 1 in lines
        assert 3 in lines
        assert 2 not in lines


# ── Multi-line Code ──────────────────────────────────────────────────────────

class TestMultiLineCode:
    """Verify multi-line code produces multiple explanations."""

    def test_springboot_controller(self, explainer):
        code = """package com.example;
import java.util.List;
@RestController
public class UserController {
    @Autowired
    private UserService service;
    @GetMapping("/users")
    public List<User> getAll() {
        return service.findAll();
    }
}"""
        result = explainer.explain(code)
        assert len(result["line_explanations"]) >= 5
        assert "rest" in result["summary"].lower() or "controller" in result["summary"].lower()


# ── Output Structure ─────────────────────────────────────────────────────────

class TestOutputStructure:
    """All outputs must have summary and line_explanations."""

    def test_result_has_summary(self, explainer):
        result = explainer.explain("def foo(): pass")
        assert "summary" in result

    def test_result_has_line_explanations(self, explainer):
        result = explainer.explain("def foo(): pass")
        assert "line_explanations" in result
        assert isinstance(result["line_explanations"], list)

    def test_each_explanation_has_line(self, explainer):
        result = explainer.explain("import os\nimport sys")
        for e in result["line_explanations"]:
            assert "line" in e
            assert isinstance(e["line"], int)

    def test_each_explanation_has_code(self, explainer):
        result = explainer.explain("import os")
        for e in result["line_explanations"]:
            assert "code" in e

    def test_each_explanation_has_explanation(self, explainer):
        result = explainer.explain("import os")
        for e in result["line_explanations"]:
            assert "explanation" in e
            assert len(e["explanation"]) > 3


# ── LLM Fallback ─────────────────────────────────────────────────────────────

class TestLLMFallback:
    """Verify graceful fallback when LLM fails."""

    def test_broken_llm_falls_back(self):
        class BrokenLLM:
            def create_chat_completion(self, **kwargs):
                raise RuntimeError("LLM offline")

        explainer = CodeExplainer(llm=BrokenLLM())
        result = explainer.explain("import os\ndef main(): pass")
        assert len(result["line_explanations"]) >= 2

    def test_no_llm_uses_rules(self, explainer):
        result = explainer.explain("@RestController\npublic class X {}")
        assert len(result["line_explanations"]) >= 2
