"""
backend/shared/operating_mode.py
=================================
Manages Operating Modes of MSA V5.0:
  - OFFLINE   : 100% local, no external HTTP/DNS calls.
  - ONLINE    : Access to cloud models, web search, external MCP tools.
  - HYBRID    : Local primary, cloud fallback.
  - ENTERPRISE: Audited tool permissions, JWT auth, TLS forced.
  - DEVELOPER : Expanded terminal permissions, hot-reloading, debug logs.
  - SAFE      : Zero-trust, no terminal execution allowed, safety guards active.
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("msa.operating_mode")


class OperatingMode(str, Enum):
    OFFLINE = "OFFLINE"
    ONLINE = "ONLINE"
    HYBRID = "HYBRID"
    ENTERPRISE = "ENTERPRISE"
    DEVELOPER = "DEVELOPER"
    SAFE = "SAFE"


class OperatingModeManager:
    """Coordinates behavior limits according to active system operating mode."""

    def __init__(self, default_mode: OperatingMode = OperatingMode.HYBRID) -> None:
        self._current_mode = default_mode
        logger.info("Operating mode initialized: %s", self._current_mode.value)

    def get_mode(self) -> OperatingMode:
        return self._current_mode

    def set_mode(self, mode: OperatingMode) -> None:
        self._current_mode = mode
        logger.info("Operating mode changed to: %s", mode.value)

    def is_internet_allowed(self) -> bool:
        """ONLINE, HYBRID, ENTERPRISE, and DEVELOPER allow internet access."""
        return self._current_mode in (
            OperatingMode.ONLINE,
            OperatingMode.HYBRID,
            OperatingMode.ENTERPRISE,
            OperatingMode.DEVELOPER
        )

    def is_terminal_allowed(self) -> bool:
        """SAFE mode blocks all terminal execution completely."""
        return self._current_mode != OperatingMode.SAFE

    def get_allowed_tools(self) -> List[str]:
        """Restrict tool usage depending on security modes."""
        if self._current_mode == OperatingMode.SAFE:
            return ["filesystem_read", "filesystem_list"]  # Read-only, no terminal
        if self._current_mode == OperatingMode.OFFLINE:
            return ["filesystem_read", "filesystem_write", "filesystem_list", "terminal", "git_status", "git_diff", "get_system_info"] # No web search
        return ["filesystem_read", "filesystem_write", "filesystem_list", "terminal", "web_search", "git_status", "git_diff", "get_system_info"]


# ── SingletonAccessor ─────────────────────────────────────────────────────────
_mode_manager: Optional[OperatingModeManager] = None

def get_operating_mode_manager() -> OperatingModeManager:
    global _mode_manager
    if _mode_manager is None:
        _mode_manager = OperatingModeManager()
    return _mode_manager
