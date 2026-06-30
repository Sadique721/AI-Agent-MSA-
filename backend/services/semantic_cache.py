import os
import sqlite3
import logging
from typing import Optional

logger = logging.getLogger("msa.services.semantic_cache")

class SemanticCache:
    def __init__(self, db_path: str = "data/semantic_cache.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT UNIQUE,
                    response TEXT,
                    model TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def get(self, query: str) -> Optional[str]:
        query_cleaned = query.strip().lower()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT response FROM cache WHERE LOWER(query) = ?", (query_cleaned,))
            row = cursor.fetchone()
            if row:
                logger.info("Semantic Cache HIT for exact query match.")
                return row[0]
            
            cursor.execute("SELECT query, response FROM cache")
            rows = cursor.fetchall()
            for db_query, db_resp in rows:
                intersection = set(query_cleaned.split()).intersection(set(db_query.lower().split()))
                union = set(query_cleaned.split()).union(set(db_query.lower().split()))
                if union:
                    sim = len(intersection) / len(union)
                    if sim >= 0.70:
                        logger.info("Semantic Cache HIT with similarity: %.2f", sim)
                        return db_resp
        return None

    def set(self, query: str, response: str, model: str = "default") -> None:
        query_cleaned = query.strip()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO cache (query, response, model)
                    VALUES (?, ?, ?)
                """, (query_cleaned, response, model))
                conn.commit()
                logger.debug("Stored response in Semantic Cache.")
        except Exception as e:
            logger.error("Failed to write to Semantic Cache: %s", e)
