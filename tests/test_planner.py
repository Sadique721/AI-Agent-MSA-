"""
tests/test_planner.py
======================
Unit tests for the Planner Agent.
Tests task categorization, single-step plans, and multi-step conjunction splitting.
"""

import pytest
from agent.Planner import PlannerAgent


def test_task_categorization():
    planner = PlannerAgent()

    assert planner.get_task_category("write a python script to parse logs") == "coding_task"
    assert planner.get_task_category("search for spring boot jobs on LinkedIn") == "browser_task"
    assert planner.get_task_category("open WhatsApp on phone") == "mobile_task"
    assert planner.get_task_category("shutdown the system") == "system_task"


def test_single_step_plan():
    planner = PlannerAgent()

    plan = planner.plan("open notepad")
    assert len(plan) == 1
    assert plan[0]["tool"] == "open_app"
    assert plan[0]["params"]["app"] == "notepad"


def test_multi_step_plan():
    planner = PlannerAgent()

    plan = planner.plan("open chrome then search for Python tutorials")
    assert len(plan) == 2
    assert plan[0]["tool"] == "open_app"
    assert plan[0]["params"]["app"] == "chrome"
    assert plan[1]["tool"] in ("internet_search", "browser_search")
