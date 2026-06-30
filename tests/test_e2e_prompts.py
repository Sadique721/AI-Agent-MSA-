"""
tests/test_e2e_prompts.py
==========================
End-to-End integration tests for all requested test prompts.
Verifies conversational, RAG, memory, and search queries return verified rich responses.
"""

import os
import sys
import pytest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agent.AgentService import AgentService
from backend.decision_engine import DecisionEngine
from indexes.sqlite_db import SQLiteMetadataStore

@pytest.fixture(scope="module")
def agent_service():
    # Setup simple in-memory or test database connection
    db_store = SQLiteMetadataStore()
    engine = DecisionEngine()
    # Force fallback or mock provider for testing predictability if needed
    service = AgentService(engine, db_store)
    return service

def test_prompt_hi(agent_service):
    res = agent_service.process_input("hi")
    assert res["status"] == "success"
    assert "response" in res
    assert len(res["response"]) > 0
    print(f"\n[hi] -> {res['response']}")

def test_prompt_what_is_java(agent_service):
    res = agent_service.process_input("what is java")
    assert res["status"] == "success"
    assert "response" in res
    assert len(res["response"]) > 0
    print(f"\n[what is java] -> {res['response']}")

def test_prompt_latest_ai_news(agent_service):
    # This triggers internet search
    res = agent_service.process_input("latest AI news")
    assert res["status"] == "success"
    assert "response" in res
    # Should not be the prefix placeholder only
    assert "Searching the web for:" not in res["response"]
    assert "Searching for" not in res["response"]
    assert len(res["response"]) > 0
    print(f"\n[latest AI news] -> {res['response']}")

def test_prompt_solve_this_code(agent_service):
    res = agent_service.process_input("solve this code: print('hello')")
    assert res["status"] == "success"
    assert "response" in res
    assert len(res["response"]) > 0
    print(f"\n[solve this code] -> {res['response']}")

def test_prompt_search_spring_boot(agent_service):
    res = agent_service.process_input("search Spring Boot documentation")
    assert res["status"] == "success"
    assert "response" in res
    assert "Searching the web for:" not in res["response"]
    assert len(res["response"]) > 0
    print(f"\n[search Spring Boot] -> {res['response']}")

def test_prompt_explain_pdf(agent_service):
    res = agent_service.process_input("explain this PDF content")
    assert res["status"] == "success"
    assert "response" in res
    assert len(res["response"]) > 0
    print(f"\n[explain this PDF] -> {res['response']}")

def test_prompt_remember_name(agent_service):
    res = agent_service.process_input("remember my name is Md Sadique Amin")
    assert res["status"] == "success"
    assert "response" in res
    assert len(res["response"]) > 0
    print(f"\n[remember my name] -> {res['response']}")

def test_prompt_what_did_i_ask_yesterday(agent_service):
    res = agent_service.process_input("what did I ask yesterday?")
    assert res["status"] == "success"
    assert "response" in res
    assert len(res["response"]) > 0
    print(f"\n[what did I ask yesterday] -> {res['response']}")
