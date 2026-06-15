"""
tests/test_validator.py
========================
Phase-2 tests for the Validator.

Covers:
  - validate_step() — LOW / MEDIUM / HIGH levels
  - validate_result() — full result set, partial failures
  - validate_final_output() — scoring and grading
  - Domain-specific checks per tool category
  - Edge cases: empty results, all pass, all fail
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.Validator import Validator, LEVEL_LOW, LEVEL_MEDIUM, LEVEL_HIGH


@pytest.fixture(scope="module")
def validator():
    return Validator()


def make_step(n, tool, action="search"):
    return {"step": n, "tool": tool, "action": action, "params": {}}


def make_result(n, tool, result_str):
    return {"step": n, "tool": tool, "action": "search", "params": {}, "result": result_str}


# ── validate_step tests ───────────────────────────────────────────────────────

class TestValidateStep:

    def test_empty_result_fails_low(self, validator):
        step = make_step(1, "browser_search")
        v    = validator.validate_step(step, "")
        assert v["valid"] is False
        assert v["level"] == LEVEL_LOW
        assert v["score"] == 0.0

    def test_none_result_fails_low(self, validator):
        step = make_step(1, "internet_search")
        v    = validator.validate_step(step, "None")
        assert v["valid"] is False

    def test_error_keyword_fails_medium(self, validator):
        step = make_step(1, "browser_navigate")
        v    = validator.validate_step(step, "Error: connection timed out")
        assert v["valid"] is False
        assert v["level"] == LEVEL_MEDIUM

    def test_tool_failed_message_fails(self, validator):
        step = make_step(1, "open_app")
        v    = validator.validate_step(step, "Tool 'open_app' failed: permission denied")
        assert v["valid"] is False

    def test_good_search_result_passes(self, validator):
        step = make_step(1, "internet_search")
        v    = validator.validate_step(step, "Python is a high-level, general-purpose programming language..." * 3)
        assert v["valid"] is True
        assert v["score"] >= 0.5

    def test_browser_linkedin_requires_job_content(self, validator):
        step = make_step(1, "browser_linkedin")
        # Result without job keywords
        v    = validator.validate_step(step, "Welcome to LinkedIn homepage")
        assert v["valid"] is False

    def test_browser_linkedin_job_content_passes(self, validator):
        step = make_step(1, "browser_linkedin")
        v    = validator.validate_step(step, "Senior Java Developer — Ahmedabad | 5+ years Spring Boot experience")
        assert v["valid"] is True

    def test_memory_remember_passes_on_any_output(self, validator):
        step = make_step(1, "memory_remember")
        v    = validator.validate_step(step, "Memory stored: id=42")
        assert v["valid"] is True

    def test_memory_search_no_results_fails(self, validator):
        step = make_step(1, "memory_search")
        v    = validator.validate_step(step, "no results found")
        assert v["valid"] is False

    def test_memory_search_with_results_passes(self, validator):
        step = make_step(1, "memory_search")
        v    = validator.validate_step(step, "[{'text': 'Spring Boot project', 'score': 0.9}]")
        assert v["valid"] is True

    def test_get_time_passes(self, validator):
        step = make_step(1, "get_time")
        v    = validator.validate_step(step, "Current time: 2026-06-05 19:15:00")
        assert v["valid"] is True

    def test_mobile_call_success(self, validator):
        step = make_step(1, "mobile_call")
        v    = validator.validate_step(step, "Call initiated successfully to 9318302850")
        assert v["valid"] is True

    def test_score_increases_with_content_length(self, validator):
        step  = make_step(1, "internet_search")
        short = validator.validate_step(step, "Hello world")
        long  = validator.validate_step(step, "A" * 300)
        if short["valid"] and long["valid"]:
            assert long["score"] >= short["score"]


# ── validate_result tests ─────────────────────────────────────────────────────

class TestValidateResult:

    def test_empty_results_fails(self, validator):
        v = validator.validate_result([])
        assert v["valid"] is False
        assert v["total"] == 0

    def test_all_pass(self, validator):
        results = [
            make_result(1, "internet_search", "Python tutorials found: 50 results matching your query"),
            make_result(2, "memory_remember", "Memory stored: id=1"),
        ]
        v = validator.validate_result(results)
        assert v["valid"] is True
        assert v["passed"] == 2
        assert v["score"] > 0.5

    def test_partial_failure(self, validator):
        results = [
            make_result(1, "browser_linkedin", "Welcome to LinkedIn homepage"),   # fails — no job content
            make_result(2, "memory_remember",  "Memory stored: id=2"),             # passes
        ]
        v = validator.validate_result(results)
        assert v["valid"] is False
        assert v["passed"] == 1
        assert len(v["failed_steps"]) == 1
        assert v["failed_steps"][0]["tool"] == "browser_linkedin"

    def test_all_fail(self, validator):
        results = [
            make_result(1, "browser_navigate", "Error: timeout"),
            make_result(2, "browser_search",   ""),
        ]
        v = validator.validate_result(results)
        assert v["valid"] is False
        assert v["passed"] == 0
        assert v["score"] == 0.0

    def test_score_range(self, validator):
        results = [
            make_result(1, "get_time",         "2026-06-05 19:00:00"),
            make_result(2, "get_profile",      "Name: Md Sadique Amin, Role: Software Engineer"),
            make_result(3, "memory_remember",  "Stored"),
        ]
        v = validator.validate_result(results)
        assert 0.0 <= v["score"] <= 1.0

    def test_reason_string_present(self, validator):
        results = [make_result(1, "internet_search", "Results found")]
        v = validator.validate_result(results)
        assert isinstance(v["reason"], str)
        assert len(v["reason"]) > 0


# ── validate_final_output tests ───────────────────────────────────────────────

class TestValidateFinalOutput:

    def test_empty_results(self, validator):
        v = validator.validate_final_output([], "Find Java jobs")
        assert v["valid"] is False
        assert v["grade"] == "F"

    def test_grade_a_high_score(self, validator):
        results = [
            make_result(1, "browser_linkedin", "Java Developer position at TCS — Ahmedabad | 3+ years experience required"),
            make_result(2, "internet_search",  "Found 50 Java developer jobs in Ahmedabad matching Spring Boot experience"),
            make_result(3, "memory_remember",  "Stored 20 Java job results in memory successfully"),
        ]
        v = validator.validate_final_output(results, "Find Java jobs in Ahmedabad")
        assert v["grade"] in ("A", "B")
        assert v["score"] >= 0.5
        assert isinstance(v["summary"], str)
        assert isinstance(v["feedback"], str)

    def test_grade_f_all_fail(self, validator):
        results = [
            make_result(1, "browser_linkedin", ""),
            make_result(2, "browser_search",   "Error: failed"),
        ]
        v = validator.validate_final_output(results, "Find jobs")
        assert v["grade"] == "F"
        assert v["valid"] is False

    def test_summary_contains_goal(self, validator):
        results = [make_result(1, "get_time", "19:15:00")]
        v = validator.validate_final_output(results, "Get current time")
        assert "Goal" in v["summary"]

    def test_all_output_fields_present(self, validator):
        results = [make_result(1, "internet_search", "Some result data here")]
        v = validator.validate_final_output(results, "Search internet")
        for field in ["valid", "score", "grade", "feedback", "summary"]:
            assert field in v, f"Missing field: {field}"

    def test_score_is_float_between_0_and_1(self, validator):
        results = [make_result(1, "get_profile", "Name: Sadique")]
        v = validator.validate_final_output(results, "Get my profile")
        assert isinstance(v["score"], float)
        assert 0.0 <= v["score"] <= 1.0
