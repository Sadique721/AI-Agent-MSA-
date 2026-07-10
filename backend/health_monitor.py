"""
backend/health_monitor.py
=========================
System health checker and telemetry API provider (V10).

Validates active connections to Ollama LLM, FAISS indices, local database locks,
available memory (OOM safety checking), and returns telemetry data.
"""
from __future__ import annotations

import logging
import time
import urllib.request
from typing import Any, Dict

import psutil

import config

logger = logging.getLogger("msa.backend.health")


class HealthMonitor:
    """
    Checks backend component health statuses and memory diagnostics.
    """

    def __init__(self) -> None:
        self._start_time = time.time()

    def check_health(self) -> Dict[str, Any]:
        """Runs availability checks and resource profiling."""
        stats = {
            "status": "healthy",
            "uptime_seconds": int(time.time() - self._start_time),
            "timestamp": time.time(),
            "resources": self._get_resources(),
            "services": {
                "ollama": self._check_ollama(),
                "faiss": self._check_faiss(),
                "sqlite": self._check_sqlite(),
            }
        }

        # If any core component is down, degrade status
        if not stats["services"]["sqlite"] or not stats["services"]["faiss"]:
            stats["status"] = "degraded"
        
        return stats

    @staticmethod
    def _get_resources() -> Dict[str, Any]:
        """Fetches RAM and CPU profile metrics."""
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=None)
        return {
            "cpu_percent": cpu,
            "ram_total_gb": round(mem.total / (1024 ** 3), 2),
            "ram_available_gb": round(mem.available / (1024 ** 3), 2),
            "ram_percent": mem.percent,
            "oom_risk": mem.percent > 90.0,
        }

    @staticmethod
    def _check_ollama() -> bool:
        """Pings Ollama local API."""
        try:
            req = urllib.request.Request(f"{config.OLLAMA_URL}/api/tags")
            with urllib.request.urlopen(req, timeout=2.0):
                return True
        except Exception:
            return False

    @staticmethod
    def _check_faiss() -> bool:
        """Checks index file exists on disk."""
        return os.path.exists(config.FAISS_INDEX_PATH)

    @staticmethod
    def _check_sqlite() -> bool:
        """Attempts a quick read from primary SQLite DB."""
        import sqlite3
        try:
            conn = sqlite3.connect(config.DB_PATH, timeout=1.0)
            conn.execute("SELECT 1").fetchone()
            conn.close()
            return True
        except Exception:
            return False


import os
