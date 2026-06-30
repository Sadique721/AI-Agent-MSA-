import pytest
from agent.workflow import (
    node_intent_detection,
    node_memory_recall,
    node_kg_search,
    node_rag_search,
    node_tool_execution,
    node_llm_generation,
    node_reflection,
    run_agent_workflow
)

def test_intent_detection_node():
    state = {"user_input": "Write a python function to add two numbers"}
    new_state = node_intent_detection(state)
    assert new_state["intent"] == "CODING"
    assert new_state["intent_confidence"] > 0.5
    assert "intent_ms" in new_state["timings"]

def test_memory_recall_node():
    state = {"user_input": "Hello", "history": []}
    new_state = node_memory_recall(state)
    assert "memory_context" in new_state
    assert isinstance(new_state["history"], list)

def test_kg_search_node():
    state = {"user_input": "FastAPI"}
    new_state = node_kg_search(state)
    assert "kg_entities" in new_state
    assert "kg_context" in new_state

def test_rag_search_node():
    state = {"user_input": "LangGraph"}
    new_state = node_rag_search(state)
    assert "rag_chunks" in new_state
    assert "rag_context" in new_state

def test_tool_execution_node():
    state = {"intent": "SYSTEM_TASK", "user_input": "list files"}
    new_state = node_tool_execution(state)
    assert "tool_results" in new_state
    assert len(new_state["tool_results"]) > 0
    assert new_state["tool_results"][0]["tool"] == "filesystem_list"
    assert new_state["tool_results"][0]["success"] is True

def test_llm_generation_node_fallback():
    state = {
        "user_input": "What is Python?",
        "intent": "GENERAL_QA",
        "reasoning_mode": "balanced",
        "persona": "default",
        "rag_context": "",
        "memory_context": "",
        "tool_summary": "",
        "timings": {}
    }
    new_state = node_llm_generation(state)
    assert "llm_response" in new_state
    assert "Ollama" in new_state["llm_response"]  # Falls back to smart simulation

def test_reflection_node_early_return():
    state = {
        "user_input": "What is Python?",
        "llm_response": "Python is a programming language.",
        "reasoning_mode": "balanced",
        "intent": "GENERAL_QA",
        "llm_model": "mock",
        "timings": {}
    }
    new_state = node_reflection(state)
    assert new_state["action"] == "langgraph_execution"
    assert new_state["parameters"]["intent"] == "GENERAL_QA"
    assert new_state["reflection_score"] == 1.0
