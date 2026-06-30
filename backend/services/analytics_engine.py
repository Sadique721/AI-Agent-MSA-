import os
import sqlite3
import logging
from typing import Dict, Any

logger = logging.getLogger("msa.services.analytics")

class AnalyticsEngine:
    def __init__(self, db_path: str = "data/analytics.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:  # nosec
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    model TEXT,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    latency_ms REAL,
                    estimated_cost REAL
                )
            """)
            conn.commit()

    def log_request(self, model: str, input_tokens: int, output_tokens: int, latency_ms: float):
        cost = (input_tokens * 0.0000015) + (output_tokens * 0.000002)
        try:
            with sqlite3.connect(self.db_path) as conn:  # nosec
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO metrics (model, input_tokens, output_tokens, latency_ms, estimated_cost)
                    VALUES (?, ?, ?, ?, ?)
                """, (model, input_tokens, output_tokens, latency_ms, cost))
                conn.commit()
                logger.info("Logged request metrics: model=%s, cost=$%.6f", model, cost)
        except Exception as e:
            logger.error("Failed logging metrics: %s", e)

    def get_aggregated_stats(self) -> Dict[str, Any]:
        try:
            with sqlite3.connect(self.db_path) as conn:  # nosec
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_requests,
                        SUM(input_tokens) as total_input_tokens,
                        SUM(output_tokens) as total_output_tokens,
                        AVG(latency_ms) as avg_latency_ms,
                        SUM(estimated_cost) as total_cost
                    FROM metrics
                """)
                row = cursor.fetchone()
                if row and row["total_requests"] is not None and row["total_requests"] > 0:
                    return dict(row)
        except Exception as e:
            logger.error("Failed to fetch metrics stats: %s", e)
        return {
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "avg_latency_ms": 0.0,
            "total_cost": 0.0
        }
