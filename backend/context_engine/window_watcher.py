"""
backend/context_engine/window_watcher.py
=========================================
Tracks the active desktop window using ctypes on Windows.
"""
from __future__ import annotations

import logging
import sys

logger = logging.getLogger("msa.context.window")


class WindowWatcher:
    """Reads active window information on Windows (with platform fallback)."""

    def __init__(self) -> None:
        self._ctypes_available = (sys.platform == "win32")

    def get_active_window(self) -> str:
        """Get the active window title."""
        if not self._ctypes_available:
            return "Terminal Shell (Unix fallback)"
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                return buf.value
            return "Desktop Overlay"
        except Exception as e:
            logger.debug("Failed to retrieve active window title: %s", e)
            return "Windows Desktop"
