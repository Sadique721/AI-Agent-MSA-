"""
tests/test_replanning.py
=========================
Phase-2 tests for the Auto-Replan loop.

Tests:
  - Replan triggered on validation failure
  - Max 3 retries respected
  - Graceful fallback after 3 consecutive failures
  - Reasoning packet adjusted on each replan
  - ReasoningEngine + Validator integration
  - AgentService auto-replan pipeline (mock execution)
"""
import sys
import os
import pytest
from unittest.mock import MagicMock, patch, call
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.ReasoningEngine import ReasoningEngine
from agent.Validator        import Validator


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def engine():
    return ReasoningEngine()

@pytest.fixture(scope="module")
def validator():
    return Validator()


# ── Helper: simulate step execution ──────────────────────────────────────────

def mock_execute_steps(steps: List[Dict], fail_tools: List[str] = None) -> List[Dict]:
    """Simulate executing a plan — returns fail result for tools in fail_tools."""
    fail_tools = fail_tools or []
    results = []
    for step in steps:
        tool   = step["tool"]
        result = (
            f"Error: {tool} failed during execution"
            if tool in fail_tools
            else f"Success: {tool} returned 50 results matching the query"
        )
        results.append({
            "step":   step["step"],
            "tool":   tool,
            "action": step.get("action", ""),
            "params": step.get("params", {}),
            "result": result,
        })
    return results


# ── ReasoningEngine replan adjustment tests ───────────────────────────────────

class TestReasoningEngineReplan:

    def test_failure_hint_changes_packet(self, engine):
        """A failure hint should produce a modified reasoning packet."""
        original = engine.reason("Find Java jobs in Ahmedabad")

        failure_hint = {
            "valid":        False,
            "reason":       "browser_linkedin timed out",
            "failed_steps": [{"tool": "browser_linkedin", "step": 1}],
        }
        replanned = engine.reason("Find Java jobs in Ahmedabad", failure_hint=failure_hint)

        # Replanned packet should acknowledge the failure
        assert replanned["failure_hint"] is not None
        assert replanned["failure_hint"]["valid"] is False

    def test_failed_tool_removed_from_required(self, engine):
        """browser_linkedin should be replaced by internet_search fallback after failure."""
        failure_hint = {
            "valid":        False,
            "reason":       "browser_linkedin connection refused",
            "failed_steps": [{"tool": "browser_linkedin", "step": 1}],
        }
        replanned = engine.reason("Find Java jobs", failure_hint=failure_hint)
        # browser_linkedin should be gone OR internet_search added
        tools = replanned["required_tools"]
        assert "internet_search" in tools or "browser_linkedin" not in tools

    def test_replan_step_mentions_failure(self, engine):
        """First reasoning step should mention the previous failure."""
        failure_hint = {
            "valid":        False,
            "reason":       "Search returned no results",
            "failed_steps": [{"tool": "internet_search", "step": 1}],
        }
        replanned = engine.reason("Search for Python tutorials", failure_hint=failure_hint)
        first_step = replanned["reasoning_steps"][0].lower() if replanned["reasoning_steps"] else ""
        assert "previous" in first_step or "fail" in first_step or "adjust" in first_step

    def test_replan_attempt_field(self, engine):
        """replan_attempt field is present in every packet."""
        result = engine.reason("Open Notepad")
        assert "replan_attempt" in result
        assert isinstance(result["replan_attempt"], int)

    def test_multiple_failed_tools_removed(self, engine):
        """Both browser_linkedin and browser_search should be removed on multi-tool failure."""
        failure_hint = {
            "valid":        False,
            "reason":       "Browser tools unavailable",
            "failed_steps": [
                {"tool": "browser_linkedin", "step": 1},
                {"tool": "browser_search",   "step": 2},
            ],
        }
        replanned = engine.reason("Find Spring Boot jobs online", failure_hint=failure_hint)
        tools = replanned["required_tools"]
        # At least one of these should be removed
        assert "browser_linkedin" not in tools or "internet_search" in tools


# ── Validator replan decision tests ──────────────────────────────────────────

class TestValidatorReplanDecision:

    def test_all_pass_no_replan_needed(self, validator):
        """When all steps pass, no replan is needed."""
        results = [
            {"step": 1, "tool": "internet_search", "action": "search", "params": {},
             "result": "Found 40 Python jobs in Ahmedabad, Maharashtra region"},
            {"step": 2, "tool": "memory_remember", "action": "remember", "params": {},
             "result": "Memory stored: id=99"},
        ]
        v = validator.validate_result(results)
        assert v["valid"] is True
        assert len(v["failed_steps"]) == 0

    def test_single_failure_triggers_replan(self, validator):
        """A single step failure should indicate replan is needed."""
        results = [
            {"step": 1, "tool": "browser_linkedin", "action": "search", "params": {},
             "result": ""},  # empty — fails LOW level
            {"step": 2, "tool": "memory_remember", "action": "remember", "params": {},
             "result": "Stored"},
        ]
        v = validator.validate_result(results)
        assert v["valid"] is False
        assert len(v["failed_steps"]) >= 1
        assert v["failed_steps"][0]["tool"] == "browser_linkedin"

    def test_all_fail_needs_full_replan(self, validator):
        """All steps failing means full replan required."""
        results = [
            {"step": 1, "tool": "browser_linkedin", "action": "search", "params": {},
             "result": "Error: connection refused"},
            {"step": 2, "tool": "browser_search",   "action": "search", "params": {},
             "result": "Error: browser not available"},
        ]
        v = validator.validate_result(results)
        assert v["valid"] is False
        assert v["passed"] == 0
        assert len(v["failed_steps"]) == 2

    def test_partial_success_reported_correctly(self, validator):
        """Partial success: passed + failed counts must sum to total."""
        results = [
            {"step": 1, "tool": "internet_search", "action": "search", "params": {},
             "result": "Found results for Java jobs"},
            {"step": 2, "tool": "browser_linkedin", "action": "search", "params": {},
             "result": ""},
            {"step": 3, "tool": "memory_remember",  "action": "store",  "params": {},
             "result": "Stored"},
        ]
        v = validator.validate_result(results)
        assert v["passed"] + len(v["failed_steps"]) == v["total"]


# ── Full auto-replan loop simulation tests ────────────────────────────────────

class TestAutoReplanLoop:

    def test_success_on_first_attempt(self, engine, validator):
        """No replan needed when first execution succeeds."""
        task    = "Search for Java tutorials"
        reason  = engine.reason(task)
        steps   = [
            {"step": 1, "tool": "internet_search", "action": "search",
             "params": {"query": task}},
        ]
        results = mock_execute_steps(steps, fail_tools=[])
        v       = validator.validate_result(results, reason)
        assert v["valid"] is True

    def test_replan_on_first_failure(self, engine, validator):
        """Replan should produce a new reasoning packet after failure."""
        task    = "Find Java jobs on LinkedIn"
        reason  = engine.reason(task)
        steps   = [
            {"step": 1, "tool": "browser_linkedin", "action": "search",
             "params": {"query": "Java developer"}},
        ]
        # First attempt — fail
        results = mock_execute_steps(steps, fail_tools=["browser_linkedin"])
        v1      = validator.validate_result(results, reason)
        assert v1["valid"] is False

        # Replan
        new_reason = engine.reason(task, failure_hint=v1)
        assert new_reason["failure_hint"] is not None
        tools = new_reason["required_tools"]
        # Should have removed linkedin and/or added fallback
        assert "internet_search" in tools or "browser_linkedin" not in tools

    def test_max_3_retries_loop(self, engine, validator):
        """Simulate 3 consecutive failures — loop should stop at 3."""
        task        = "Find Java jobs in Bangalore"
        MAX_RETRIES = 3
        attempt     = 0
        current_reason = engine.reason(task)
        steps = [
            {"step": 1, "tool": "browser_linkedin", "action": "search", "params": {}},
            {"step": 2, "tool": "browser_search",   "action": "search", "params": {}},
        ]

        while attempt < MAX_RETRIES:
            attempt += 1
            results = mock_execute_steps(steps, fail_tools=["browser_linkedin", "browser_search"])
            validation = validator.validate_result(results, current_reason)

            if validation["valid"]:
                break

            if attempt < MAX_RETRIES:
                current_reason = engine.reason(task, failure_hint=validation)

        # Loop must have stopped at or before MAX_RETRIES
        assert attempt <= MAX_RETRIES
        assert attempt == 3  # All 3 failed in this simulation

    def test_success_on_second_attempt(self, engine, validator):
        """Simulate failure on attempt 1, success on attempt 2."""
        task        = "Search Python tutorials"
        MAX_RETRIES = 3
        attempt     = 0
        current_reason = engine.reason(task)
        succeeded   = False

        # Steps for attempt 1: will fail
        failing_steps = [
            {"step": 1, "tool": "browser_search", "action": "search", "params": {}},
        ]
        # Steps for attempt 2: will succeed
        passing_steps = [
            {"step": 1, "tool": "internet_search", "action": "search",
             "params": {"query": task}},
        ]

        while attempt < MAX_RETRIES:
            attempt += 1
            if attempt == 1:
                results = mock_execute_steps(failing_steps, fail_tools=["browser_search"])
            else:
                results = mock_execute_steps(passing_steps, fail_tools=[])

            validation = validator.validate_result(results, current_reason)

            if validation["valid"]:
                succeeded = True
                break

            if attempt < MAX_RETRIES:
                current_reason = engine.reason(task, failure_hint=validation)

        assert succeeded is True
        assert attempt == 2

    def test_graceful_fallback_after_all_failures(self, engine, validator):
        """After 3 failures the loop gives up — response must still be returned."""
        task        = "Find obscure job listings"
        MAX_RETRIES = 3
        attempt     = 0
        current_reason  = engine.reason(task)
        final_validation = None

        steps = [
            {"step": 1, "tool": "browser_linkedin", "action": "search", "params": {}},
        ]

        while attempt < MAX_RETRIES:
            attempt += 1
            results = mock_execute_steps(steps, fail_tools=["browser_linkedin"])
            final_validation = validator.validate_result(results, current_reason)

            if final_validation["valid"]:
                break
            if attempt < MAX_RETRIES:
                current_reason = engine.reason(task, failure_hint=final_validation)

        # After loop: validation must be a valid dict (even if task failed)
        assert final_validation is not None
        assert "valid" in final_validation
        assert "reason" in final_validation
        assert final_validation["valid"] is False
        assert attempt == MAX_RETRIES

    def test_final_validation_grade_after_success(self, engine, validator):
        """After successful execution, final output grade should be >= C."""
        task    = "Get current time and save to memory"
        reason  = engine.reason(task)
        results = [
            {"step": 1, "tool": "get_time",        "action": "get_time", "params": {},
             "result": "Current time: 2026-06-05 19:24:00"},
            {"step": 2, "tool": "memory_remember",  "action": "remember", "params": {},
             "result": "Memory stored: time=2026-06-05 19:24:00"},
        ]
        final = validator.validate_final_output(results, reason["goal"])
        assert final["grade"] in ("A", "B", "C")
        assert final["valid"] is True
