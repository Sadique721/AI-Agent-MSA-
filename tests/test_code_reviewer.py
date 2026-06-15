"""
tests/test_code_reviewer.py
=============================
Unit tests for coding/CodeReviewer.py — Phase-3 Coding Agent.
Covers security, performance, SOLID, grading, edge cases, LLM fallback.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coding.CodeReviewer import CodeReviewer


@pytest.fixture
def reviewer():
    """CodeReviewer without LLM (rule-based only)."""
    return CodeReviewer(llm=None)


# ── Security: Hardcoded Secrets ───────────────────────────────────────────────

class TestHardcodedSecrets:
    """Detect hardcoded API keys, passwords, secrets."""

    def test_hardcoded_api_key_detected(self, reviewer):
        code = 'String api_key = "sk_live_12345";'
        result = reviewer.review(code)
        assert any("security" in c.lower() or "hardcoded" in c.lower() for c in result["comments"])
        assert result["score"] < 1.0

    def test_hardcoded_password_detected(self, reviewer):
        code = 'String password = "admin123";'
        result = reviewer.review(code)
        assert any("security" in c.lower() for c in result["comments"])

    def test_hardcoded_secret_detected(self, reviewer):
        code = 'const secret = "my_secret_token";'
        result = reviewer.review(code)
        assert any("security" in c.lower() for c in result["comments"])

    def test_env_reference_not_flagged(self, reviewer):
        code = 'api_key = os.environ.get("API_KEY")'
        result = reviewer.review(code)
        # Should NOT flag when env is referenced
        security_comments = [c for c in result["comments"] if "security" in c.lower() and "hardcoded" in c.lower()]
        assert len(security_comments) == 0

    def test_properties_reference_not_flagged(self, reviewer):
        code = 'password = properties.get("db.password")'
        result = reviewer.review(code)
        security_comments = [c for c in result["comments"] if "hardcoded" in c.lower()]
        assert len(security_comments) == 0


# ── Security: SQL Injection ──────────────────────────────────────────────────

class TestSQLInjection:
    """Detect SQL injection via string concatenation."""

    def test_sql_concat_detected(self, reviewer):
        code = 'String query = "SELECT * FROM users WHERE name = \'" + userInput + "\'"'
        result = reviewer.review(code)
        assert any("sql" in c.lower() for c in result["comments"])
        assert result["score"] < 1.0

    def test_sql_like_concat_detected(self, reviewer):
        code = 'String q = "SELECT * FROM data WHERE title LIKE \'%" + search + "%\'"'
        result = reviewer.review(code)
        assert any("sql" in c.lower() for c in result["comments"])

    def test_parameterized_query_not_flagged(self, reviewer):
        code = """cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))"""
        result = reviewer.review(code)
        sql_comments = [c for c in result["comments"] if "sql injection" in c.lower()]
        assert len(sql_comments) == 0


# ── Performance: Nested Loops ────────────────────────────────────────────────

class TestNestedLoops:
    """Detect O(N²) nested for loops."""

    def test_nested_loops_detected(self, reviewer):
        code = """for (int i = 0; i < n; i++) {
    for (int j = 0; j < m; j++) {
        System.out.println(i + j);
    }
}"""
        result = reviewer.review(code)
        assert any("performance" in c.lower() or "nested" in c.lower() for c in result["comments"])

    def test_single_loop_not_flagged(self, reviewer):
        code = """for (int i = 0; i < 10; i++) {
    System.out.println(i);
}"""
        result = reviewer.review(code)
        nested_comments = [c for c in result["comments"] if "nested" in c.lower()]
        assert len(nested_comments) == 0


# ── Architecture: Large Class ────────────────────────────────────────────────

class TestLargeClass:
    """Detect large class blocks (>150 lines)."""

    def test_large_class_flagged(self, reviewer):
        code = "\n".join([f"int x{i} = {i};" for i in range(160)])
        result = reviewer.review(code)
        assert any("architecture" in c.lower() or "large" in c.lower() for c in result["comments"])
        assert result["score"] < 1.0

    def test_small_class_not_flagged(self, reviewer):
        code = "\n".join([f"int x{i} = {i};" for i in range(10)])
        result = reviewer.review(code)
        arch_comments = [c for c in result["comments"] if "large" in c.lower()]
        assert len(arch_comments) == 0


# ── Clean Code (No Issues) ───────────────────────────────────────────────────

class TestCleanCode:
    """Clean code should get readability praise and high score."""

    def test_clean_code_gets_readability_comment(self, reviewer):
        code = """public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
}"""
        result = reviewer.review(code)
        assert any("readability" in c.lower() or "clean" in c.lower() or "modular" in c.lower() for c in result["comments"])

    def test_clean_code_grade_a(self, reviewer):
        code = """public class Adder {
    public int add(int a, int b) {
        return a + b;
    }
}"""
        result = reviewer.review(code)
        assert result["grade"] == "A"
        assert result["score"] == 1.0

    def test_clean_code_valid_true(self, reviewer):
        code = "def add(a, b): return a + b"
        result = reviewer.review(code)
        assert result["valid"] is True


# ── Grade Calculation ────────────────────────────────────────────────────────

class TestGradeCalculation:
    """Verify grade boundaries."""

    def test_grade_a_for_clean(self, reviewer):
        code = "int x = 1;"
        result = reviewer.review(code)
        assert result["grade"] == "A"
        assert result["score"] >= 0.9

    def test_grade_reduced_by_secret(self, reviewer):
        code = 'String api_key = "secret_123";'
        result = reviewer.review(code)
        assert result["score"] < 1.0
        assert result["grade"] in ("A", "B", "C", "D", "F")

    def test_grade_f_for_severe_issues(self, reviewer):
        # SQL injection (-25) + hardcoded secret (-20) + large class (-10) = score 45
        lines = ['String api_key = "key123";']
        lines.append('String query = "SELECT * FROM users WHERE name = \'" + input + "\'";')
        lines.extend([f"// line {i}" for i in range(160)])
        code = "\n".join(lines)
        result = reviewer.review(code)
        assert result["score"] < 0.5
        assert result["grade"] == "F"
        assert result["valid"] is False

    def test_valid_false_below_70(self, reviewer):
        # SQL injection alone = -25 + hardcoded = -20 = score 55
        code = 'String api_key = "x";\nString q = "SELECT * FROM t WHERE id = \'" + id + "\'";'
        result = reviewer.review(code)
        assert result["score"] <= 0.55
        assert result["valid"] is False


# ── Multiple Issues ──────────────────────────────────────────────────────────

class TestMultipleIssues:
    """Multiple issues should accumulate deductions."""

    def test_secret_and_sql_injection(self, reviewer):
        code = '''String password = "admin";
String query = "SELECT * FROM users WHERE name = '" + input + "'";'''
        result = reviewer.review(code)
        assert len(result["comments"]) >= 2
        assert result["score"] < 0.6

    def test_all_deductions_accumulate(self, reviewer):
        lines = ['String secret = "abc";']
        lines.append('String q = "SELECT * FROM t WHERE id = \'" + x + "\'";')
        lines.extend([f"// line {i}" for i in range(160)])
        code = "\n".join(lines)
        result = reviewer.review(code)
        # 100 - 20 (secret) - 25 (sql) - 10 (large) = 45
        assert result["score"] <= 0.45


# ── Output Structure ─────────────────────────────────────────────────────────

class TestOutputStructure:
    """All outputs must have score, grade, comments, valid."""

    def test_result_has_score(self, reviewer):
        result = reviewer.review("int x = 1;")
        assert "score" in result
        assert isinstance(result["score"], float)
        assert 0.0 <= result["score"] <= 1.0

    def test_result_has_grade(self, reviewer):
        result = reviewer.review("int x = 1;")
        assert "grade" in result
        assert result["grade"] in ("A", "B", "C", "D", "F")

    def test_result_has_comments(self, reviewer):
        result = reviewer.review("int x = 1;")
        assert "comments" in result
        assert isinstance(result["comments"], list)
        assert len(result["comments"]) > 0

    def test_result_has_valid(self, reviewer):
        result = reviewer.review("int x = 1;")
        assert "valid" in result
        assert isinstance(result["valid"], bool)


# ── Edge Cases ───────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Edge case handling."""

    def test_empty_code(self, reviewer):
        result = reviewer.review("")
        assert result["grade"] == "A"

    def test_single_line(self, reviewer):
        result = reviewer.review("x = 1")
        assert result["score"] == 1.0

    def test_code_with_only_comments(self, reviewer):
        code = "// This is a clean file\n// No issues here"
        result = reviewer.review(code)
        assert result["grade"] == "A"


# ── LLM Fallback ─────────────────────────────────────────────────────────────

class TestLLMFallback:
    """Verify graceful fallback when LLM fails."""

    def test_broken_llm_falls_back(self):
        class BrokenLLM:
            def create_chat_completion(self, **kwargs):
                raise RuntimeError("LLM offline")

        reviewer = CodeReviewer(llm=BrokenLLM())
        result = reviewer.review("int x = 1;")
        assert result["grade"] == "A"

    def test_no_llm_uses_rules(self, reviewer):
        result = reviewer.review('String api_key = "abc";')
        assert any("security" in c.lower() for c in result["comments"])
