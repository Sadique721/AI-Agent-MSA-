"""
career/analytics.py
===================
Funnel statistics, response rates, and reporting engine (V9).

Aggregates conversion rates from discovered -> queued -> applied -> interviews -> offers
and outputs JSON metrics and daily/weekly summaries.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List

from config import APPLICATIONS_DB, ANALYTICS_REPORT_DIR

logger = logging.getLogger("msa.career.analytics")


class CareerAnalytics:
    """
    Computes performance metrics and generates periodic job reports.
    """

    def __init__(self) -> None:
        os.makedirs(ANALYTICS_REPORT_DIR, exist_ok=True)
        self._db = sqlite3.connect(APPLICATIONS_DB)

    def get_funnel_stats(self) -> Dict[str, int]:
        """Calculates count of applications in each pipeline phase."""
        stats = {
            "discovered": 0, "queued": 0, "applied": 0,
            "interview": 0, "rejected": 0, "offer": 0,
        }
        try:
            rows = self._db.execute("SELECT status, COUNT(*) FROM applications GROUP BY status").fetchall()
            for status, count in rows:
                if status in stats:
                    stats[status] = count
        except Exception as exc:
            logger.error("[Analytics] Funnel query failed: %s", exc)
        return stats

    def get_response_rates(self) -> Dict[str, Any]:
        """Calculates recruiter response rates and interview rates."""
        try:
            total_applied = self._db.execute(
                "SELECT COUNT(*) FROM applications WHERE status NOT IN ('discovered', 'queued')"
            ).fetchone()[0] or 0

            responses = self._db.execute(
                "SELECT COUNT(*) FROM applications WHERE status IN ('interview', 'rejected', 'offer')"
            ).fetchone()[0] or 0

            interviews = self._db.execute(
                "SELECT COUNT(*) FROM applications WHERE status='interview'"
            ).fetchone()[0] or 0

            offers = self._db.execute(
                "SELECT COUNT(*) FROM applications WHERE status='offer'"
            ).fetchone()[0] or 0

            resp_rate = (responses / total_applied) if total_applied > 0 else 0.0
            int_rate = (interviews / total_applied) if total_applied > 0 else 0.0
            off_rate = (offers / total_applied) if total_applied > 0 else 0.0

            return {
                "total_applied": total_applied,
                "total_responses": responses,
                "response_rate": round(resp_rate, 4),
                "interview_rate": round(int_rate, 4),
                "offer_rate": round(off_rate, 4),
            }
        except Exception as exc:
            logger.error("[Analytics] Rates calculation failed: %s", exc)
            return {"total_applied": 0, "total_responses": 0, "response_rate": 0.0, "interview_rate": 0.0, "offer_rate": 0.0}

    def generate_report(self, days: int = 7) -> Dict[str, Any]:
        """Generates comprehensive metrics summary for the past N days."""
        now = datetime.utcnow()
        since = (now - timedelta(days=days)).isoformat()

        report = {
            "period_days": days,
            "generated_at": now.isoformat(),
            "funnel": self.get_funnel_stats(),
            "rates": self.get_response_rates(),
            "applied_in_period": 0,
            "source_distribution": {},
        }

        try:
            # Query applications submitted in period
            rows = self._db.execute(
                "SELECT job_id, applied_at FROM applications WHERE applied_at >= ?", (since,)
            ).fetchall()
            report["applied_in_period"] = len(rows)
        except Exception as exc:
            logger.debug("[Analytics] Period query failed: %s", exc)

        return report

    def save_report_to_disk(self, days: int = 7) -> str:
        """Persists the JSON report to the configured analytics folder."""
        data = self.generate_report(days)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"career_report_{days}d_{ts}.json"
        path = os.path.join(ANALYTICS_REPORT_DIR, filename)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info("[Analytics] Report written: %s", path)
            return path
        except Exception as exc:
            logger.error("[Analytics] Write report failed: %s", exc)
            return ""
