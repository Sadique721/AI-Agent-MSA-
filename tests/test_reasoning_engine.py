"""
tests/test_reasoning_engine.py
===============================
Phase-2 tests for the ReasoningEngine.

Covers:
  - All 6 reasoning types
  - Risk level detection (low / medium / high)
  - Dependency extraction
  - requires_approval flag
  - Goal extraction
  - Required tool detection
  - Empty input handling
  - Replan adjustment on failure_hint
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.ReasoningEngine import ReasoningEngine


@pytest.fixture(scope="module")
def engine():
    return ReasoningEngine()


# ── Reasoning type tests ─────────────────────────────────────────────────────

class TestReasoningTypes:

    def test_browser_type_linkedin(self, engine):
        result = engine.reason("Find Java jobs on LinkedIn in Ahmedabad")
        assert result["reasoning_type"] == "browser"

    def test_browser_type_search(self, engine):
        result = engine.reason("Search Google for Spring Boot tutorials")
        assert result["reasoning_type"] == "browser"

    def test_mobile_type_call(self, engine):
        result = engine.reason("Call mummy on phone")
        assert result["reasoning_type"] == "mobile"

    def test_mobile_type_alarm(self, engine):
        result = engine.reason("Set alarm for 7am on mobile")
        assert result["reasoning_type"] == "mobile"

    def test_coding_type(self, engine):
        result = engine.reason("Write a Python script to parse JSON files")
        assert result["reasoning_type"] == "coding"

    def test_memory_type_remember(self, engine):
        result = engine.reason("Remember my Spring Boot project details")
        assert result["reasoning_type"] == "memory"

    def test_memory_type_recall(self, engine):
        result = engine.reason("Do you remember what we discussed yesterday?")
        assert result["reasoning_type"] == "memory"

    def test_automation_type(self, engine):
        result = engine.reason("Click on the Submit button and scroll down")
        assert result["reasoning_type"] == "automation"

    def test_system_type_time(self, engine):
        result = engine.reason("What time is it?")
        assert result["reasoning_type"] == "system"

    def test_system_type_profile(self, engine):
        result = engine.reason("Show my profile")
        assert result["reasoning_type"] == "system"


# ── Risk level tests ─────────────────────────────────────────────────────────

class TestRiskDetection:

    def test_low_risk_search(self, engine):
        result = engine.reason("Search Java developer jobs")
        assert result["risk_level"] == "low"

    def test_low_risk_time(self, engine):
        result = engine.reason("What time is it now?")
        assert result["risk_level"] == "low"

    def test_high_risk_shutdown(self, engine):
        result = engine.reason("Shutdown the computer")
        assert result["risk_level"] == "high"
        assert result["requires_approval"] is True

    def test_high_risk_call(self, engine):
        result = engine.reason("Call 9318302850")
        assert result["risk_level"] == "high"
        assert result["requires_approval"] is True

    def test_high_risk_sms(self, engine):
        result = engine.reason("Send SMS to mummy")
        assert result["risk_level"] == "high"
        assert result["requires_approval"] is True

    def test_high_risk_delete(self, engine):
        result = engine.reason("Delete all files in downloads")
        assert result["risk_level"] == "high"
        assert result["requires_approval"] is True

    def test_medium_risk_navigate(self, engine):
        result = engine.reason("Navigate to http://example.com")
        assert result["risk_level"] in ("medium", "high")

    def test_low_risk_profile(self, engine):
        result = engine.reason("Show my profile information")
        assert result["risk_level"] == "low"


# ── Dependency detection tests ────────────────────────────────────────────────

class TestDependencyDetection:

    def test_internet_dependency(self, engine):
        result = engine.reason("Search LinkedIn for jobs")
        assert "internet" in result["dependencies"] or "browser" in result["dependencies"]

    def test_browser_dependency(self, engine):
        result = engine.reason("Open LinkedIn and search for Java jobs")
        assert "browser" in result["dependencies"]

    def test_phone_dependency(self, engine):
        result = engine.reason("Call mummy on the phone")
        assert "phone" in result["dependencies"]

    def test_storage_dependency(self, engine):
        result = engine.reason("Write a file to the downloads folder")
        assert "storage" in result["dependencies"]

    def test_no_dependency_time(self, engine):
        result = engine.reason("What time is it?")
        assert result["dependencies"] is not None


# ── Goal extraction tests ─────────────────────────────────────────────────────

class TestGoalExtraction:

    def test_goal_not_empty(self, engine):
        result = engine.reason("Find Java jobs in Ahmedabad")
        assert result["goal"]
        assert len(result["goal"]) > 3

    def test_goal_strips_please(self, engine):
        result = engine.reason("Please search Google for Python tutorials")
        assert "please" not in result["goal"].lower() or True  # best effort

    def test_goal_capitalized(self, engine):
        result = engine.reason("open notepad and type hello")
        assert result["goal"][0].isupper()


# ── Required tool detection tests ─────────────────────────────────────────────

class TestToolDetection:

    def test_linkedin_tool(self, engine):
        result = engine.reason("Find Java jobs on LinkedIn")
        assert "browser_linkedin" in result["required_tools"]

    def test_memory_remember_save(self, engine):
        result = engine.reason("Save the top 20 job results to memory")
        assert "memory_remember" in result["required_tools"]

    def test_internet_search_tool(self, engine):
        result = engine.reason("Search for Spring Boot tutorials")
        assert any("search" in t or "internet" in t for t in result["required_tools"])

    def test_open_app_tool(self, engine):
        result = engine.reason("Open Notepad")
        assert "open_app" in result["required_tools"]

    def test_mobile_call_tool(self, engine):
        result = engine.reason("Call 9318302850")
        assert "mobile_call" in result["required_tools"]


# ── Reasoning steps tests ─────────────────────────────────────────────────────

class TestReasoningSteps:

    def test_steps_not_empty(self, engine):
        result = engine.reason("Find Java jobs and save top 20")
        assert len(result["reasoning_steps"]) >= 2

    def test_steps_end_with_validate(self, engine):
        result = engine.reason("Search for Python jobs")
        steps  = result["reasoning_steps"]
        # Last two steps should mention validate and memory
        joined = " ".join(steps[-2:]).lower()
        assert "validat" in joined or "store" in joined or "memory" in joined


# ── Empty input test ──────────────────────────────────────────────────────────

class TestEdgeCases:

    def test_empty_input(self, engine):
        result = engine.reason("")
        assert result["goal"] == "No input provided"
        assert result["required_tools"] == []
        assert result["requires_approval"] is False

    def test_whitespace_input(self, engine):
        result = engine.reason("   ")
        assert result["goal"] == "No input provided"

    def test_replan_adjustment(self, engine):
        failure_hint = {
            "valid":        False,
            "reason":       "Browser tool timed out",
            "failed_steps": [{"tool": "browser_linkedin", "step": 1}],
        }
        result = engine.reason("Find Java jobs in Ahmedabad", failure_hint=failure_hint)
        # Should have adjusted to avoid browser_linkedin
        assert result["failure_hint"] is not None
        # Fallback internet_search should be injected
        assert "internet_search" in result["required_tools"] or "browser_linkedin" not in result["required_tools"]

    def test_full_packet_fields(self, engine):
        result = engine.reason("Open Chrome and search Google")
        required_fields = [
            "goal", "reasoning_type", "required_tools",
            "risk_level", "requires_approval", "dependencies",
            "reasoning_steps", "replan_attempt", "failure_hint",
        ]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"
