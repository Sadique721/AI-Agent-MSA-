"""
ai_core/ai_router.py
=====================
Intelligent Model Selection Router for MSA AI Agent V5.0.
Selects the best model based on task type, reasoning mode, and availability.
Uses config/models.yaml routing table.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Dict, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger("msa.core.router")


class AIRouter:
    """
    Selects the optimal model for a given task type and reasoning mode.

    Priority:
      1. Config/models.yaml task_routing table
      2. Reasoning mode override
      3. Availability check (Ollama ping)
      4. Fallback chain
    """

    # Static fallback chain when config unavailable
    _FALLBACK_CHAIN = [
        "ollama/llama3.2:3b",
        "ollama/phi3:mini",
        "ollama/mistral:7b",
    ]

    _TASK_TO_MODE: Dict[str, str] = {
        "CODING":           "coding",
        "DEBUGGING":        "debug",
        "CODE_REVIEW":      "coding",
        "TESTING":          "coding",
        "RESEARCH":         "research",
        "SUMMARIZATION":    "fast",
        "QUESTION_ANSWER":  "balanced",
        "ARCHITECTURE":     "architect",
        "MATH":             "deep_thinking",
        "CREATIVE_WRITING": "balanced",
        "VISION":           "balanced",
        "SYSTEM_TASK":      "balanced",
        "GENERAL_QA":       "balanced",
        "AUTONOMOUS":       "autonomous",
    }

    def __init__(self) -> None:
        self._config: Optional[Dict] = None
        self._load_config()

    def _load_config(self) -> None:
        try:
            from backend.shared.config_loader import ConfigLoader
            cfg = ConfigLoader.get()
            self._config = cfg.as_dict().get("models", {})
            logger.info("AIRouter loaded model config")
        except Exception as e:
            logger.debug("Config unavailable for AIRouter: %s", e)

    def select_model(
        self,
        task_type: str = "GENERAL_QA",
        reasoning_mode: Optional[str] = None,
        context_size: int = 0,
        prefer_fast: bool = False,
    ) -> str:
        """
        Select the best model identifier string.
        Returns e.g. "ollama/llama3.2:3b" or "gpt-4o-mini".
        """
        # Determine mode
        if reasoning_mode:
            mode = reasoning_mode
        else:
            mode = self._TASK_TO_MODE.get(task_type.upper(), "balanced")

        if prefer_fast:
            mode = "fast"

        # Long context adjustment
        if context_size > 6000 and mode not in ("fast",):
            mode = "deep_thinking"

        # Get model from config
        if self._config:
            modes = self._config.get("reasoning_modes", {})
            mode_cfg = modes.get(mode, modes.get("balanced", {}))
            primary = mode_cfg.get("primary", "")
            if primary:
                if self._is_available(primary):
                    return primary
                # Try fallback
                fallback = mode_cfg.get("fallback", "")
                if fallback and self._is_available(fallback):
                    logger.info("Primary '%s' unavailable — using fallback '%s'", primary, fallback)
                    return fallback

        # Static fallback chain
        for model in self._FALLBACK_CHAIN:
            if self._is_available(model):
                return model

        # Final fallback — return primary anyway (LiteLLM will handle error)
        return "ollama/llama3.2:3b"

    def _is_available(self, model: str) -> bool:
        """
        Quick availability check.
        For Ollama models: ping localhost:11434.
        For cloud models: check if API key env var is set.
        Returns True if available, False otherwise.
        Does NOT raise exceptions.
        """
        if model.startswith("ollama/"):
            return self._check_ollama()
        # Cloud models — check API key
        provider_keys = {
            "gpt-": "OPENAI_API_KEY",
            "claude-": "ANTHROPIC_API_KEY",
            "gemini": "GOOGLE_API_KEY",
            "groq": "GROQ_API_KEY",
        }
        for prefix, env_key in provider_keys.items():
            if prefix in model.lower():
                return bool(os.environ.get(env_key))
        return True  # Unknown model — assume available

    def _check_ollama(self) -> bool:
        try:
            import urllib.request
            ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            req = urllib.request.Request(f"{ollama_url}/api/tags")
            with urllib.request.urlopen(req, timeout=2):
                return True
        except Exception:
            return False

    def get_routing_table(self) -> Dict[str, str]:
        """Return task_type → recommended_model mapping."""
        result = {}
        for task, mode in self._TASK_TO_MODE.items():
            result[task] = self.select_model(task_type=task, reasoning_mode=mode)
        return result


# ── Module singleton ──────────────────────────────────────────────────────────
_router: Optional[AIRouter] = None


def get_ai_router() -> AIRouter:
    global _router
    if _router is None:
        _router = AIRouter()
    return _router
