import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from backend.gateway_server import app
from agent.workflow import run_agent_workflow

client = TestClient(app)

def test_gateway_status():
    response = client.get("/api/v5/status")
    assert response.status_code == 200
    data = response.json()
    assert data["gateway"] == "FastAPI V5.0"
    assert data["status"] == "online"

@patch("backend.gateway_server._agent_service")
def test_gateway_execution_success(mock_service):
    # Mock successful agent service processing
    mock_service.process_input.return_value = {
        "response": "Hello World program",
        "action": "chat",
        "parameters": {}
    }
    response = client.post("/api/v5/execute", json={"command": "Write a Hello World program in python"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "response" in data

def test_gateway_execution_degraded():
    # When service is None or uninitialized, should degrade gracefully
    with patch("backend.gateway_server._agent_service", None):
        response = client.post("/api/v5/execute", json={"command": "Write a Hello World program in python"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert "pending" in data["response"]

@patch("agent.llm_agent.LLMAgent.generate")
@patch("agent.intent_agent.IntentAgent.classify")
def test_langgraph_workflow(mock_classify, mock_generate):
    # Mock intent agent to match the test assertion
    mock_classify.return_value = {
        "intent": "Goal extraction",
        "confidence": 0.95,
        "method": "mock",
        "secondary_intents": []
    }
    # Mock LLM agent to return "langgraph" response
    from agent.llm_agent import LLMResponse
    mock_generate.return_value = LLMResponse("This response is processed by langgraph.", "mock_model")

    result = run_agent_workflow("Verify workspace status")
    assert "response" in result
    assert "langgraph" in result["response"]
    assert result["action"] == "langgraph_execution"
    assert "Goal extraction" in result["parameters"]["intent"]
