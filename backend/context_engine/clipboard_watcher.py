"""
backend/context_engine/clipboard_watcher.py
============================================
Retrieves Windows clipboard contents without external dependencies.
"""
from __future__ import annotations

import logging
import subprocess
import sys

logger = logging.getLogger("msa.context.clipboard")


class ClipboardWatcher:
    """Watches and retrieves clipboard data using native OS utilities."""

    def __init__(self) -> None:
        self._last_content = ""

    def get_text(self) -> str:
        """Fetch current text content of clipboard."""
        try:
            if sys.platform == "win32":
                # Call PowerShell's Get-Clipboard
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                    capture_output=True, text=True, timeout=1.5
                )
                text = res.stdout.strip()
                if text:
                    self._last_content = text
                    return text
            elif sys.platform == "darwin":
                # macOS pbpaste
                res = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=1.5)
                return res.stdout.strip()
            else:
                # Linux xclip
                res = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True, timeout=1.5)
                return res.stdout.strip()
        except Exception as e:
            logger.debug("Failed to read clipboard: %s", e)
        return self._last_content
