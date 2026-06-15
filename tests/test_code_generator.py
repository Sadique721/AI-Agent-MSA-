"""
tests/test_code_generator.py
=============================
Unit tests for coding/CodeGenerator.py — Phase-3 Coding Agent.
Covers all language generators, auto-detection, LLM fallback, edge cases.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coding.CodeGenerator import CodeGenerator


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def gen():
    """CodeGenerator without LLM (rule-based only)."""
    return CodeGenerator(llm=None)


# ── Auto-detection Tests ─────────────────────────────────────────────────────

class TestLanguageAutoDetection:
    """Verify automatic language/framework detection from prompts."""

    def test_detect_springboot_keyword(self, gen):
        result = gen.generate("Create a Spring Boot CRUD API for Customer")
        assert result["language"] == "springboot"

    def test_detect_springboot_variant(self, gen):
        result = gen.generate("Generate SpringBoot REST controller")
        assert result["language"] == "springboot"

    def test_detect_angular_keyword(self, gen):
        result = gen.generate("Create an Angular login component")
        assert result["language"] == "angular"

    def test_detect_java_keyword(self, gen):
        result = gen.generate("Write a Java class for validation")
        assert result["language"] == "java"

    def test_detect_sql_keyword(self, gen):
        result = gen.generate("Generate SQL table for users")
        assert result["language"] == "sql"

    def test_detect_sql_via_database(self, gen):
        result = gen.generate("Create a database schema for orders")
        assert result["language"] == "sql"

    def test_detect_python_keyword(self, gen):
        result = gen.generate("Write a Python script to search customers")
        assert result["language"] == "python"

    def test_detect_python_via_pytest(self, gen):
        result = gen.generate("Create a pytest test suite")
        assert result["language"] == "python"

    def test_detect_javascript_keyword(self, gen):
        result = gen.generate("Write a JavaScript REST API")
        assert result["language"] == "javascript"

    def test_detect_javascript_via_node(self, gen):
        result = gen.generate("Create a Node express server")
        assert result["language"] == "javascript"

    def test_default_to_python(self, gen):
        result = gen.generate("Create something amazing")
        assert result["language"] == "python"


# ── Explicit Language Override ────────────────────────────────────────────────

class TestExplicitLanguage:
    """Verify explicit language parameter overrides auto-detection."""

    def test_explicit_java(self, gen):
        result = gen.generate("Create something", language="java")
        assert result["language"] == "java"

    def test_explicit_sql(self, gen):
        result = gen.generate("Create something", language="sql")
        assert result["language"] == "sql"

    def test_explicit_javascript(self, gen):
        result = gen.generate("Create something", language="javascript")
        assert result["language"] == "javascript"

    def test_explicit_python(self, gen):
        result = gen.generate("Create something", language="python")
        assert result["language"] == "python"


# ── Spring Boot Generation ───────────────────────────────────────────────────

class TestSpringBootGeneration:
    """Verify Spring Boot CRUD generation produces all 4 files."""

    def test_springboot_returns_4_files(self, gen):
        result = gen.generate_springboot("Create API for Customer")
        assert result["language"] == "springboot"
        assert len(result["files"]) == 4

    def test_springboot_controller_file(self, gen):
        result = gen.generate_springboot("Create entity Customer")
        paths = [f["path"] for f in result["files"]]
        assert any("Controller.java" in p for p in paths)

    def test_springboot_service_file(self, gen):
        result = gen.generate_springboot("Create entity Customer")
        paths = [f["path"] for f in result["files"]]
        assert any("Service.java" in p for p in paths)

    def test_springboot_repository_file(self, gen):
        result = gen.generate_springboot("Create entity Customer")
        paths = [f["path"] for f in result["files"]]
        assert any("Repository.java" in p for p in paths)

    def test_springboot_model_file(self, gen):
        result = gen.generate_springboot("Create entity Customer")
        paths = [f["path"] for f in result["files"]]
        # Model file should contain the entity name
        model_files = [f for f in result["files"] if "model" in f["path"]]
        assert len(model_files) == 1

    def test_springboot_controller_has_rest_annotations(self, gen):
        result = gen.generate_springboot("entity Customer")
        ctrl = [f for f in result["files"] if "Controller" in f["path"]][0]
        assert "@RestController" in ctrl["content"]
        assert "@GetMapping" in ctrl["content"]
        assert "@PostMapping" in ctrl["content"]

    def test_springboot_explanation_present(self, gen):
        result = gen.generate_springboot("entity Customer")
        assert "explanation" in result
        assert len(result["explanation"]) > 10

    def test_springboot_entity_name_extraction(self, gen):
        result = gen.generate_springboot("Create API for Product entity")
        # Should extract "Product" as entity name
        ctrl = [f for f in result["files"] if "Controller" in f["path"]][0]
        assert "Product" in ctrl["path"]


# ── Angular Generation ───────────────────────────────────────────────────────

class TestAngularGeneration:
    """Verify Angular component generation (TS, HTML, CSS)."""

    def test_angular_returns_3_files(self, gen):
        result = gen.generate_angular("Create login component")
        assert result["language"] == "angular"
        assert len(result["files"]) == 3

    def test_angular_ts_file(self, gen):
        result = gen.generate_angular("Create login component")
        ts_files = [f for f in result["files"] if f["path"].endswith(".ts")]
        assert len(ts_files) == 1
        assert "@Component" in ts_files[0]["content"]

    def test_angular_html_file(self, gen):
        result = gen.generate_angular("Create login component")
        html_files = [f for f in result["files"] if f["path"].endswith(".html")]
        assert len(html_files) == 1
        assert "<form" in html_files[0]["content"]

    def test_angular_css_file(self, gen):
        result = gen.generate_angular("Create login component")
        css_files = [f for f in result["files"] if f["path"].endswith(".css")]
        assert len(css_files) == 1


# ── SQL Generation ───────────────────────────────────────────────────────────

class TestSQLGeneration:
    """Verify SQL schema generation."""

    def test_sql_returns_single_file(self, gen):
        result = gen.generate_sql("Create table customers")
        assert result["language"] == "sql"
        assert len(result["files"]) == 1

    def test_sql_contains_create_table(self, gen):
        result = gen.generate_sql("Create table customers")
        assert "CREATE TABLE" in result["files"][0]["content"]

    def test_sql_contains_crud(self, gen):
        result = gen.generate_sql("Create table customers")
        content = result["files"][0]["content"]
        assert "INSERT INTO" in content
        assert "SELECT" in content
        assert "UPDATE" in content
        assert "DELETE FROM" in content


# ── Python Generation ────────────────────────────────────────────────────────

class TestPythonGeneration:
    """Verify Python script generation."""

    def test_python_returns_single_file(self, gen):
        result = gen.generate_python("Create search function")
        assert result["language"] == "python"
        assert len(result["files"]) == 1

    def test_python_has_def_keyword(self, gen):
        result = gen.generate_python("Create search function")
        assert "def " in result["files"][0]["content"]

    def test_python_has_main_block(self, gen):
        result = gen.generate_python("Create search function")
        assert '__name__ == "__main__"' in result["files"][0]["content"]


# ── JavaScript Generation ────────────────────────────────────────────────────

class TestJavaScriptGeneration:
    """Verify Node.js Express generation."""

    def test_javascript_returns_single_file(self, gen):
        result = gen.generate_javascript("Create REST server")
        assert result["language"] == "javascript"
        assert len(result["files"]) == 1

    def test_javascript_uses_express(self, gen):
        result = gen.generate_javascript("Create REST server")
        assert "express" in result["files"][0]["content"]

    def test_javascript_has_endpoints(self, gen):
        result = gen.generate_javascript("Create REST server")
        content = result["files"][0]["content"]
        assert "app.get" in content
        assert "app.post" in content


# ── Java Generation ──────────────────────────────────────────────────────────

class TestJavaGeneration:
    """Verify plain Java class generation."""

    def test_java_returns_single_file(self, gen):
        result = gen.generate_java("Create class CustomerService")
        assert result["language"] == "java"
        assert len(result["files"]) == 1

    def test_java_has_class_definition(self, gen):
        result = gen.generate_java("Create class CustomerService")
        assert "public class" in result["files"][0]["content"]

    def test_java_has_package(self, gen):
        result = gen.generate_java("Create class CustomerService")
        assert "package" in result["files"][0]["content"]


# ── Class Name Extraction ────────────────────────────────────────────────────

class TestClassNameExtraction:
    """Verify _extract_class_name helper."""

    def test_extracts_after_class_keyword(self, gen):
        name = gen._extract_class_name("Create class ProductService now", "Default")
        assert name == "ProductService"

    def test_extracts_after_entity_keyword(self, gen):
        name = gen._extract_class_name("entity Order mapping", "Default")
        assert name == "Order"

    def test_extracts_after_for_keyword(self, gen):
        name = gen._extract_class_name("Create API for Inventory", "Default")
        assert name == "Inventory"

    def test_returns_default_when_no_match(self, gen):
        name = gen._extract_class_name("do something", "FallbackName")
        assert name == "FallbackName"

    def test_strips_punctuation(self, gen):
        name = gen._extract_class_name("Create class Customer.", "Default")
        assert name == "Customer"


# ── LLM Fallback ─────────────────────────────────────────────────────────────

class TestLLMFallback:
    """Verify graceful fallback when LLM is not available or fails."""

    def test_no_llm_uses_rule_based(self, gen):
        result = gen.generate("Create a Spring Boot API")
        # Should not raise, should fall through to rule-based
        assert result["language"] == "springboot"

    def test_broken_llm_falls_back(self):
        class BrokenLLM:
            def create_chat_completion(self, **kwargs):
                raise RuntimeError("LLM offline")

        gen = CodeGenerator(llm=BrokenLLM())
        result = gen.generate("Generate Python search")
        # Should gracefully fall back to rule-based
        assert result["language"] == "python"


# ── Output Structure Validation ──────────────────────────────────────────────

class TestOutputStructure:
    """Verify all outputs conform to expected schema."""

    def test_result_has_language_key(self, gen):
        result = gen.generate("Create Python script")
        assert "language" in result

    def test_result_has_files_key(self, gen):
        result = gen.generate("Create Python script")
        assert "files" in result
        assert isinstance(result["files"], list)

    def test_result_has_explanation_key(self, gen):
        result = gen.generate("Create Python script")
        assert "explanation" in result

    def test_each_file_has_path_and_content(self, gen):
        result = gen.generate("Create Spring Boot CRUD")
        for f in result["files"]:
            assert "path" in f
            assert "content" in f
            assert len(f["content"]) > 0
