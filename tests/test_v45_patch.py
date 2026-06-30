import pytest
from ai_core.llm_manager import LLMManager

def test_llm_manager_fallback():
    manager = LLMManager()
    
    # Asserting that the fallback responds with custom templates offline
    response = manager.generate("Write a Hello World program in python")
    assert "print" in response
    assert "Hello, World!" in response

def test_llm_manager_circuit_breaker():
    manager = LLMManager()
    # Trip circuit breaker by simulating failures
    for _ in range(5):
        manager._handle_failure()
        
    assert manager.circuit_broken is True
    
    # Assert that even when circuit is broken, the fallback returns content successfully
    response = manager.generate("Write a Hello World program in java")
    assert "public class Main" in response

def test_llm_manager_streaming():
    manager = LLMManager()
    tokens = []
    
    def callback(t):
        tokens.append(t)
        
    manager.generate("Write a Hello World program in python", stream_callback=callback)
    assert len(tokens) > 0
    full_text = "".join(tokens)
    assert "print" in full_text
