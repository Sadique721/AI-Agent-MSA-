import time
import pytest
from infrastructure.service_registry import BaseService, ServiceRegistry
from infrastructure.dependency_injection import Container
from infrastructure.event_bus import EventBus, Event
from backend.planner.planner_agent import PlannerAgent, TaskNode, TaskGraph
from backend.planner.orchestration_engine import OrchestrationEngine

# Dummy class for testing DI
class DependencyClass:
    pass

class DependentClass:
    def __init__(self, dep: DependencyClass):
        self.dep = dep

# Dummy service for testing ServiceRegistry
class DummyService(BaseService):
    pass

def test_dependency_injection():
    """Verify Container resolves bindings and constructs nested parameters correctly."""
    container = Container()
    container.clear()
    
    container.register_singleton(DependencyClass, DependencyClass)
    container.register_transient(DependentClass, DependentClass)

    dep_instance = container.resolve(DependencyClass)
    assert isinstance(dep_instance, DependencyClass)

    dependent_instance = container.resolve(DependentClass)
    assert isinstance(dependent_instance, DependentClass)
    assert dependent_instance.dep is dep_instance

def test_service_registry():
    """Verify ServiceRegistry monitors liveness and logs state transitions."""
    registry = ServiceRegistry()
    registry.shutdown_all()
    
    dummy = DummyService()
    registry.register("Dummy", dummy)

    assert registry.get("Dummy") is dummy
    assert dummy.is_running is False

    dummy.start()
    assert dummy.is_running is True
    assert registry.list_services()["Dummy"]["status"] == "healthy"

    dummy.stop()
    assert dummy.is_running is False
    assert registry.list_services()["Dummy"]["status"] == "stopped"

def test_event_bus():
    """Verify EventBus processes async events and handles subscriber notifications."""
    event_bus = EventBus()
    event_bus.start()

    events_received = []
    def on_event(event):
        events_received.append(event)

    event_bus.subscribe("test.topic", on_event)
    event_bus.publish("test.topic", "hello_world")

    # Allow processing time
    time.sleep(0.1)

    assert len(events_received) == 1
    assert events_received[0].topic == "test.topic"
    assert events_received[0].data == "hello_world"

    event_bus.unsubscribe("test.topic", on_event)
    event_bus.stop()

def test_planner_and_orchestrator():
    """Verify PlannerAgent decomposes tasks and Orchestrator executes dependencies."""
    planner = PlannerAgent()
    orchestrator = OrchestrationEngine()

    # Decompose standard query
    graph = planner.decompose("what is java")
    
    # We should have nodes created
    assert len(graph.nodes) > 0

    # Register MemoryAgent & ValidatorAgent mock handlers into orchestrator
    class MockAgent:
        def recall(self, query):
            return "Mock memory hits for Java"
        def process(self, query):
            return "Mock processing done"

    mock_memory = MockAgent()
    mock_validator = MockAgent()

    orchestrator.register_agent("MemoryAgent", mock_memory)
    orchestrator.register_agent("ValidatorAgent", mock_validator)

    # Execute graph
    resolved_graph = orchestrator.execute_workflow(graph)
    assert resolved_graph.is_complete() is True
    assert resolved_graph.has_failures() is False
