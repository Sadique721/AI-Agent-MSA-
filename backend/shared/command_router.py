"""
backend/shared/command_router.py
=================================
Slash Command Router for MSA AI Agent V5.0.
Routes commands (e.g. /fix, /explain, /persona) to the appropriate helper or agent pipeline.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("msa.commands.router")


class CommandRouter:
    """Interceptors and routes slash commands directly to workflows or settings managers."""

    def __init__(self) -> None:
        pass

    def is_command(self, text: str) -> bool:
        return text.strip().startswith("/")

    def route(self, text: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Intercept slash commands.
        Returns: (intercepted: bool, result_payload: dict)
        """
        parts = text.strip().split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command == "/persona":
            return self._handle_persona(args)
        if command == "/workspace":
            return self._handle_workspace(args)
        if command == "/explain":
            return self._handle_workflow_command(text, "Explain this code:")
        if command == "/fix":
            return self._handle_workflow_command(text, "Fix this issue:")
        if command == "/test":
            return self._handle_workflow_command(text, "Generate tests for this:")
        
        # General pass-through for other commands (runs them via LangGraph workflow)
        if command in [
            "/deploy", "/commit", "/search", "/summarize", "/review", 
            "/document", "/run", "/plugin", "/skill", "/backup", "/restore"
        ]:
            return True, {
                "response": f"Executing command '{command}' with arguments: '{args}' via LangGraph pipeline.",
                "action": "langgraph_execution",
                "parameters": {"command": command, "args": args}
            }

        return False, {}

    def _handle_persona(self, args: str) -> Tuple[bool, Dict[str, Any]]:
        from backend.persona_manager.persona_service import get_persona_service
        service = get_persona_service()
        if not args:
            names = list(service.list_personas().keys())
            active = service.get_active_persona_name()
            return True, {
                "response": f"Active persona: **{active}**\nAvailable: {', '.join(names)}",
                "action": "persona_change",
                "parameters": {"active": active}
            }
        
        target = args.strip().lower()
        if service.set_active_persona(target):
            return True, {
                "response": f"Switched AI persona to **{target}**.",
                "action": "persona_change",
                "parameters": {"active": target}
            }
        return True, {
            "response": f"Error: Persona '{target}' not found.",
            "action": "error",
            "parameters": {}
        }

    def _handle_workspace(self, args: str) -> Tuple[bool, Dict[str, Any]]:
        from backend.workspace_manager.workspace_service import get_workspace_service
        service = get_workspace_service()
        if not args:
            all_ws = [ws.id for ws in service.list_workspaces()]
            active = service.get_active_workspace().id
            return True, {
                "response": f"Active workspace: **{active}**\nAvailable workspaces: {', '.join(all_ws)}",
                "action": "workspace_change",
                "parameters": {"active": active}
            }
        
        target = args.strip().lower()
        if service.set_active_workspace(target):
            return True, {
                "response": f"Switched workspace to **{target}**.",
                "action": "workspace_change",
                "parameters": {"active": target}
            }
        return True, {
            "response": f"Error: Workspace '{target}' not found.",
            "action": "error",
            "parameters": {}
        }

    def _handle_workflow_command(self, full_text: str, prefix: str) -> Tuple[bool, Dict[str, Any]]:
        # Let this execute via LangGraph workflow but rewrite the query to be clearer
        return True, {
            "response": f"Routing query to agent graph...",
            "action": "langgraph_execution",
            "parameters": {"rewrite": f"{prefix} {full_text}"}
        }


# ── SingletonAccessor ─────────────────────────────────────────────────────────
_command_router: Optional[CommandRouter] = None

def get_command_router() -> CommandRouter:
    global _command_router
    if _command_router is None:
        _command_router = CommandRouter()
    return _command_router
