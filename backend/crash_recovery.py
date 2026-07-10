"""
backend/crash_recovery.py
=========================
Automatic crash diagnostics and state recovery (V10).

Saves structured system checkpoint states before launching intensive scripts,
and automatically analyzes unclean shutdowns at startup.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from config import LOG_DIR, PROJECT_ROOT

logger = logging.getLogger("msa.backend.crash")
_CRASH_CHECKPOINT_FILE = os.path.join(LOG_DIR, "crash_state.json")


class CrashRecovery:
    """
    Performs startup crash inspection and saves critical checkpoints.
    """

    def __init__(self) -> None:
        os.makedirs(LOG_DIR, exist_ok=True)

    def write_checkpoint(self, state: Dict[str, Any]) -> None:
        """Saves current state snapshot before performing intensive tasks."""
        try:
            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "state": state
            }
            with open(_CRASH_CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            logger.warning("[CrashRecovery] Write checkpoint failed: %s", exc)

    def check_for_crash(self) -> Optional[Dict[str, Any]]:
        """
        Determines if previous shutdown was unclean.
        Returns the saved checkpoint state if a crash is suspected.
        """
        if not os.path.exists(_CRASH_CHECKPOINT_FILE):
            return None
        try:
            with open(_CRASH_CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.warning("[CrashRecovery] Suspected unclean shutdown detected. Checkpoint state: %s",
                           data.get("timestamp"))
            return data
        except Exception:
            return None

    def clear_checkpoint(self) -> None:
        """Called upon successful exit or safe startup cleanup."""
        if os.path.exists(_CRASH_CHECKPOINT_FILE):
            try:
                os.remove(_CRASH_CHECKPOINT_FILE)
            except Exception:
                pass

    def log_crash(self, type_, value, tb) -> None:
        """Logs global unhandled exception tracebacks."""
        trace = "".join(traceback.format_exception(type_, value, tb))
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = os.path.join(LOG_DIR, f"crash_traceback_{timestamp}.log")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(trace)
            logger.critical("[CrashRecovery] Unhandled exception crashed server. Trace log written: %s", path)
        except Exception as e:
            logger.error("[CrashRecovery] Log traceback failed: %s", e)
