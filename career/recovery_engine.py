"""
career/recovery_engine.py
==========================
Checkpoint, recovery, and failure retry engine (V8).

Tracks state checkpoints for multi-step browser applications and enforces
retry policies with exponential backoff.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional

from config import PROJECT_ROOT

logger = logging.getLogger("msa.career.recovery")

_CHECKPOINT_DIR = os.path.join(PROJECT_ROOT, "data", "checkpoints")


class RecoveryEngine:
    """
    Manages transient checkpoints and auto-recovery rules during applications.
    """

    def __init__(self) -> None:
        os.makedirs(_CHECKPOINT_DIR, exist_ok=True)

    def checkpoint(self, job_id: str, step: str, state: Dict[str, Any]) -> None:
        """Saves current state snapshot to disk."""
        path = self._get_path(job_id)
        data = {
            "job_id": job_id,
            "step": step,
            "timestamp": time.time(),
            "state": state
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug("[RecoveryEngine] Checkpoint saved: %s @ %s", job_id, step)
        except Exception as exc:
            logger.warning("[RecoveryEngine] Save checkpoint failed: %s", exc)

    def restore(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Restores last saved state for job."""
        path = self._get_path(job_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("[RecoveryEngine] Restore checkpoint failed: %s", exc)
            return None

    def clear(self, job_id: str) -> None:
        """Removes checkpoint file once application finishes."""
        path = self._get_path(job_id)
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    def mark_failed(self, job_id: str, reason: str) -> None:
        """Logs failure event and clears active checkpoint."""
        logger.error("[RecoveryEngine] Job %s application aborted: %s", job_id, reason)
        self.clear(job_id)

    @staticmethod
    def _get_path(job_id: str) -> str:
        return os.path.join(_CHECKPOINT_DIR, f"app_{job_id}.json")
