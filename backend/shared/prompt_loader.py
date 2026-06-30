"""
backend/shared/prompt_loader.py
================================
Loads prompt templates from the prompts/ directory.
Supports {{variable}} substitution and caching.
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("msa.prompts")


class PromptLoader:
    """
    Reads Markdown prompt files from the prompts/ directory and caches them.
    Supports {{variable}} template substitution.

    Usage:
        pl = PromptLoader.get()
        prompt = pl.render("coder", context="...", language="Python")
    """

    _instance: Optional["PromptLoader"] = None
    _cache: Dict[str, str] = {}

    def __init__(self, prompts_dir: Optional[Path] = None) -> None:
        if prompts_dir is None:
            here = Path(__file__).resolve()
            project_root = here.parent.parent.parent
            prompts_dir = project_root / "prompts"
        self._prompts_dir = Path(prompts_dir)
        self._cache = {}

    @classmethod
    def get_instance(cls) -> "PromptLoader":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def _load(self, name: str) -> str:
        """Load a prompt file by name (without extension)."""
        if name in self._cache:
            return self._cache[name]

        for ext in [".md", ".txt", ".prompt"]:
            path = self._prompts_dir / f"{name}{ext}"
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8").strip()
                    self._cache[name] = content
                    logger.debug("Loaded prompt: %s", name)
                    return content
                except Exception as e:
                    logger.warning("Failed to load prompt %s: %s", name, e)

        logger.warning("Prompt not found: %s (using fallback)", name)
        return f"You are MSA AI Agent V5.0. Answer the user's request: {name}"

    def get(self, name: str) -> str:
        """Get raw prompt text."""
        return self._load(name)

    def render(self, prompt_name: str, **kwargs: str) -> str:
        """
        Load prompt and substitute {{variable}} placeholders.

        Example:
            pl.render("coder", language="Python", task="write unit tests")
        """
        template = self._load(prompt_name)
        for key, value in kwargs.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        # Warn about un-substituted variables
        remaining = re.findall(r"\{\{(\w+)\}\}", template)
        if remaining:
            logger.debug("Unresolved prompt variables in '%s': %s", prompt_name, remaining)
        return template

    def list_available(self) -> list[str]:
        """List all available prompt names."""
        if not self._prompts_dir.exists():
            return []
        names = []
        for f in self._prompts_dir.iterdir():
            if f.suffix in [".md", ".txt", ".prompt"]:
                names.append(f.stem)
        return sorted(names)

    def invalidate(self, name: str) -> None:
        """Clear cached prompt (triggers reload on next access)."""
        self._cache.pop(name, None)

    def invalidate_all(self) -> None:
        """Clear all cached prompts."""
        self._cache.clear()


# Convenience module-level instance
@lru_cache(maxsize=1)
def get_prompt_loader() -> PromptLoader:
    return PromptLoader.get_instance()
