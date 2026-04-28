"""
backend/system_monitor.py
=========================
NEW MODULE — System resource monitoring via psutil.

Provides real-time CPU, RAM, Disk, and uptime information
for the /api/system_info endpoint and UI dashboard.
"""

import logging
import platform
import time
from datetime import datetime, timedelta
from typing import Dict, Any

logger = logging.getLogger("msa.system_monitor")

try:
    import psutil
    _PSUTIL_OK = True
except ImportError:
    _PSUTIL_OK = False
    logger.warning("psutil not installed. System monitor will return stub data. Run: pip install psutil")

_START_TIME = time.time()


class SystemMonitor:
    """Collects real-time system resource metrics."""

    # -----------------------------------------------------------------------
    def get_snapshot(self) -> Dict[str, Any]:
        """
        Returns a full system snapshot dict.

        Keys: cpu_percent, ram_percent, ram_used_gb, ram_total_gb,
              disk_percent, disk_used_gb, disk_total_gb,
              uptime_seconds, uptime_human, platform, hostname
        """
        if not _PSUTIL_OK:
            return self._stub_snapshot()

        try:
            cpu = psutil.cpu_percent(interval=0.3)

            ram = psutil.virtual_memory()
            ram_pct  = ram.percent
            ram_used = round(ram.used  / (1024 ** 3), 2)
            ram_total= round(ram.total / (1024 ** 3), 2)

            disk = psutil.disk_usage("/") if platform.system() != "Windows" else psutil.disk_usage("C:\\")
            disk_pct  = disk.percent
            disk_used = round(disk.used  / (1024 ** 3), 2)
            disk_total= round(disk.total / (1024 ** 3), 2)

            uptime_s = int(time.time() - psutil.boot_time())
            uptime_h = str(timedelta(seconds=uptime_s))

            return {
                "cpu_percent":   cpu,
                "ram_percent":   ram_pct,
                "ram_used_gb":   ram_used,
                "ram_total_gb":  ram_total,
                "disk_percent":  disk_pct,
                "disk_used_gb":  disk_used,
                "disk_total_gb": disk_total,
                "uptime_seconds":uptime_s,
                "uptime_human":  uptime_h,
                "platform":      platform.system(),
                "hostname":      platform.node(),
                "python":        platform.python_version(),
                "timestamp":     datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error("SystemMonitor.get_snapshot error: %s", e)
            return self._stub_snapshot()

    # -----------------------------------------------------------------------
    @staticmethod
    def _stub_snapshot() -> Dict[str, Any]:
        return {
            "cpu_percent":   0.0,
            "ram_percent":   0.0,
            "ram_used_gb":   0.0,
            "ram_total_gb":  0.0,
            "disk_percent":  0.0,
            "disk_used_gb":  0.0,
            "disk_total_gb": 0.0,
            "uptime_seconds":0,
            "uptime_human":  "N/A (psutil missing)",
            "platform":      platform.system(),
            "hostname":      platform.node(),
            "python":        platform.python_version(),
            "timestamp":     datetime.now().isoformat(),
        }

    # -----------------------------------------------------------------------
    def get_cpu_temp(self) -> float | None:
        """Returns CPU temperature in Celsius if available (Linux/Mac only)."""
        if not _PSUTIL_OK:
            return None
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for key in ("coretemp", "cpu_thermal", "cpu-thermal"):
                    if key in temps:
                        return temps[key][0].current
        except Exception:
            pass
        return None
