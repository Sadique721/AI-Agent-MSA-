"""
backend/context_engine/context_aggregator.py
============================================
Aggregates clipboard, active window, and workspace git status into unified prompt context.
"""
from __future__ import annotations

import logging
from typing import Dict
from backend.shared.config_loader import ConfigLoader
from backend.context_engine.clipboard_watcher import ClipboardWatcher
from backend.context_engine.window_watcher import WindowWatcher
from backend.context_engine.git_context import GitContext

logger = logging.getLogger("msa.context.aggregator")


class ContextAggregator:
    """Coordinates various local desktop context components."""

    def __init__(self) -> None:
        self._cfg = ConfigLoader.get_instance()
        self._clipboard = ClipboardWatcher()
        self._window = WindowWatcher()
        self._git = GitContext()

    def get_context(self, workspace_path: str = ".") -> Dict[str, str]:
        """Collect current system context."""
        context = {}

        if self._cfg.feature("enable_context_engine"):
            # Active window
            context["active_window"] = self._window.get_active_window()

            # Clipboard context
            clip_text = self._clipboard.get_text()
            if clip_text and len(clip_text) < 1000:  # Ignore massive payloads
                context["clipboard"] = clip_text

            # Git repo context
            git_ctx = self._git.get_context(workspace_path)
            if git_ctx:
                context["git"] = git_ctx

        return context

    def get_formatted_context(self, workspace_path: str = ".") -> str:
        """Format the aggregated context for LLM prompt builder injection."""
        ctx = self.get_context(workspace_path)
        if not ctx:
            return ""

        lines = ["[DESKTOP CONTEXT]"]
        if "active_window" in ctx:
            lines.append(f"Active Application: {ctx['active_window']}")
        if "clipboard" in ctx:
            lines.append(f"Clipboard Contents:\n---\n{ctx['clipboard']}\n---")
        if "git" in ctx:
            lines.append(f"Git Status:\n{ctx['git']}")
        lines.append("[END DESKTOP CONTEXT]")
        
        return "\n".join(lines)


# ── SingletonAccessor ─────────────────────────────────────────────────────────
_aggregator: Optional[ContextAggregator] = None

def get_context_aggregator() -> ContextAggregator:
    global _aggregator
    if _aggregator is None:
        _aggregator = ContextAggregator()
    return _aggregator
