"""
backend/persona_manager/persona_service.py
===========================================
Persona Service for MSA V5.0.
Manages listing, loading, switching, and retrieving custom prompts for AI personas.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional
from backend.shared.config_loader import ConfigLoader
from backend.shared.prompt_loader import PromptLoader

logger = logging.getLogger("msa.personas")


class PersonaService:
    """Orchestrates AI personas and resolves their prompts."""

    def __init__(self) -> None:
        self._cfg = ConfigLoader.get_instance()
        self._pl = PromptLoader.get_instance()
        self._active_persona = "default"

    def list_personas(self) -> Dict[str, Dict]:
        """Get all persona definitions from config."""
        return self._cfg.get_all_personas()

    def get_persona(self, name: str) -> Optional[Dict]:
        """Get a single persona by name."""
        return self._cfg.get_persona(name)

    def get_active_persona_name(self) -> str:
        return self._active_persona

    def set_active_persona(self, name: str) -> bool:
        personas = self.list_personas()
        if name in personas:
            self._active_persona = name
            logger.info("Persona set to: %s", name)
            return True
        logger.warning("Attempted to set invalid persona: %s", name)
        return False

    def get_persona_prompt(self, name: str) -> str:
        """
        Load prompt file specified in the persona config.
        Falls back to default persona prompt if missing.
        """
        persona = self.get_persona(name)
        if not persona:
            persona = self.get_persona("default") or {}

        prompt_file = persona.get("prompt_file", "prompts/persona_default.md")
        # Extract filename stem (e.g. prompts/persona_developer.md -> persona_developer)
        import os
        stem = os.path.splitext(os.path.basename(prompt_file))[0]
        
        try:
            return self._pl.get(stem)
        except Exception:
            return f"You are the {name} persona. Tone: {persona.get('tone', 'helpful')}."


# ── SingletonAccessor ─────────────────────────────────────────────────────────
_persona_service: Optional[PersonaService] = None

def get_persona_service() -> PersonaService:
    global _persona_service
    if _persona_service is None:
        _persona_service = PersonaService()
    return _persona_service
