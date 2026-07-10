"""
backend/error_reporter.py
=========================
Structured error tracking, logging, and notifications (V10).

Saves detailed diagnostic tracebacks to data/logs/errors.log and issues
Socket.IO alert notifications to the desktop client interface.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

from config import LOG_DIR

logger = logging.getLogger("msa.backend.errors")
_ERROR_LOG_PATH = os.path.join(LOG_DIR, "errors.log")


class ErrorReporter:
    """
    Captures system failures and publishes alerts to the user interface.
    """

    def __init__(self) -> None:
        os.makedirs(LOG_DIR, exist_ok=True)

    def report_error(
        self,
        exc: Exception,
        context: Optional[Dict[str, Any]] = None,
        notify: bool = True,
    ) -> str:
        """
        Logs error event with full traceback details to errors.log.
        Returns a formatted JSON error summary.
        """
        tb = traceback.format_exc()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        filename = "Unknown"
        line_no = 0
        if exc_tb:
            filename = os.path.basename(exc_tb.tb_frame.f_code.co_filename)
            line_no = exc_tb.tb_lineno

        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": exc.__class__.__name__,
            "message": str(exc),
            "file": filename,
            "line": line_no,
            "context": context or {},
            "traceback": tb,
        }

        # Write to dedicated errors.log
        try:
            with open(_ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(summary) + "\n")
            logger.error("[ErrorReporter] Captured exception: %s @ %s:%d",
                         summary["error_type"], filename, line_no)
        except Exception as e:
            logger.error("[ErrorReporter] Write failed: %s", e)

        # Notify active UI client via socket.io
        if notify:
            self._notify_frontend(summary)

        return summary["message"]

    @staticmethod
    def _notify_frontend(summary: Dict[str, Any]) -> None:
        try:
            from backend.server import socketio
            socketio.emit("error_alert", {
                "error_type": summary["error_type"],
                "message": summary["message"],
                "file": summary["file"],
                "line": summary["line"],
                "timestamp": summary["timestamp"],
            })
        except Exception:
            pass  # socketio may not be running in offline scripts/tests
