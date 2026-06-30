import os
import pytest
from fastapi.testclient import TestClient
from backend.gateway_server import app
from backend.mcp.mcp_registry import get_mcp_registry
from backend.mcp.mcp_client import MCPClient
from backend.services.code_indexer import CodeIndexer
from backend.services.semantic_cache import SemanticCache
from backend.services.analytics_engine import AnalyticsEngine

@pytest.fixture(autouse=True)
def cleanup_test_data():
    yield
    for path in ["data/test_code_index.db", "data/test_semantic_cache.db", "data/test_analytics.db"]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

def test_mcp_registry():
    registry = get_mcp_registry()
    registry.register_server("test-server", "echo", ["hello"])
    server = registry.get_server("test-server")
    assert server is not None
    assert server["command"] == "echo"
    assert any(s["name"] == "sqlite-mcp" for s in registry.list_servers())

def test_mcp_client_simulation():
    client = MCPClient("test-mcp", "cmd", ["args"])
    tools = client.list_tools()
    assert len(tools) > 0
    assert tools[0]["name"] == "test-mcp_query"
    
    call_res = client.call_tool("test-mcp_query", {"query": "hello"})
    assert "content" in call_res

def test_code_indexer():
    db_path = "data/test_code_index.db"
    indexer = CodeIndexer(db_path=db_path)
    
    test_py = "data/mock_code.py"
    os.makedirs(os.path.dirname(test_py), exist_ok=True)
    with open(test_py, "w", encoding="utf-8") as f:
        f.write("class MockClass:\n    pass\n\ndef mock_func():\n    pass\n")
        
    indexer.index_file(test_py)
    
    symbols = indexer.search_symbols("Mock")
    assert len(symbols) >= 1
    assert any(s["symbol_name"] == "MockClass" for s in symbols)
    
    if os.path.exists(test_py):
        os.remove(test_py)

def test_semantic_cache():
    db_path = "data/test_semantic_cache.db"
    cache = SemanticCache(db_path=db_path)
    
    cache.set("how do I restart the server?", "Run python main.py", model="gpt-4")
    
    ans1 = cache.get("how do I restart the server?")
    assert ans1 == "Run python main.py"
    
    ans2 = cache.get("How do I restart my server?")
    assert ans2 == "Run python main.py"

def test_analytics_engine():
    db_path = "data/test_analytics.db"
    engine = AnalyticsEngine(db_path=db_path)
    
    engine.log_request("gpt-4", 100, 200, 450.0)
    stats = engine.get_aggregated_stats()
    
    assert stats["total_requests"] == 1
    assert stats["total_input_tokens"] == 100
    assert stats["total_output_tokens"] == 200
    assert stats["avg_latency_ms"] == 450.0
    assert stats["total_cost"] > 0

def test_analytics_endpoint():
    client = TestClient(app)
    response = client.get("/api/v5/analytics")
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data
