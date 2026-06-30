import os
import pytest
import asyncio
from backend.workspace_manager.workspace_service import get_workspace_service
from backend.persona_manager.persona_service import get_persona_service
from backend.context_engine.context_aggregator import get_context_aggregator
from backend.artifact_engine.artifact_service import get_artifact_service
from backend.shared.event_bus import get_event_bus
from backend.shared.command_router import get_command_router

def test_workspaces():
    ws_service = get_workspace_service()
    # List workspaces
    workspaces = ws_service.list_workspaces()
    assert len(workspaces) >= 1
    assert any(ws.id == "default" for ws in workspaces)

    # Create workspace
    new_ws = ws_service.create_workspace("Test Project", "For testing purposes")
    assert new_ws.id == "test_project"
    assert new_ws.name == "Test Project"

    # Switch workspace
    assert ws_service.set_active_workspace("test_project") is True
    assert ws_service.get_active_workspace().id == "test_project"

    # Delete workspace
    assert ws_service.delete_workspace("test_project") is True
    assert ws_service.get_active_workspace().id == "default"

def test_personas():
    persona_service = get_persona_service()
    personas = persona_service.list_personas()
    assert "default" in personas
    assert "developer" in personas

    # Switch persona
    assert persona_service.set_active_persona("developer") is True
    assert persona_service.get_active_persona_name() == "developer"

    # Retrieve prompt
    prompt = persona_service.get_persona_prompt("developer")
    assert "Dev" in prompt or "developer" in prompt

def test_context_engine():
    aggregator = get_context_aggregator()
    formatted = aggregator.get_formatted_context()
    # If context engine is enabled, it should produce formatted lines
    assert "[DESKTOP CONTEXT]" in formatted or formatted == ""

def test_artifacts():
    art_service = get_artifact_service()
    # Create artifact
    art = art_service.create_artifact(
        title="Sample Code",
        file_type="code",
        content="print('Hello')",
        language="python"
    )
    assert art.id == "sample_code"
    assert art.current_version == 1

    # Update artifact
    updated = art_service.update_artifact("sample_code", "print('Hello World')", "added world")
    assert updated.current_version == 2
    assert updated.versions[-1].content == "print('Hello World')"
    assert updated.versions[-1].description == "added world"

    # Clean up
    assert art_service.delete_artifact("sample_code") is True

def test_event_bus():
    eb = get_event_bus()
    received = []

    def handler(event):
        received.append(event)

    eb.subscribe("test-topic", handler)
    
    # Run async function using asyncio.run
    asyncio.run(eb.publish("test-topic", {"data": "ok"}))
    
    assert len(received) == 1
    assert received[0]["data"] == "ok"
    
    eb.unsubscribe("test-topic", handler)

def test_command_router():
    router = get_command_router()
    assert router.is_command("/persona developer") is True
    assert router.is_command("hello") is False

    intercepted, result = router.route("/persona developer")
    assert intercepted is True
    assert result["action"] == "persona_change"
    assert result["parameters"]["active"] == "developer"
