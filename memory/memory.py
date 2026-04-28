"""
memory/memory.py
================
Encrypted SQLite-backed conversation memory for MSA Agent.

FIX LOG:
  - Added threading.Lock() around ALL DB operations to prevent
    race conditions under concurrent Flask requests.
  - Added limit parameter default to get_recent_context()
  - Added get_stats() method for dashboard
"""

import logging
import os
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger("msa.memory")


class Memory:
    """
    Stores and retrieves encrypted conversation history using SQLite.

    Thread-safe: all DB operations are protected by a reentrant lock.
    """

    def __init__(self, security, db_path: str = "data/memory/msa.db"):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.sec = security
        self._lock = threading.Lock()  # FIX: thread-safety

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._create_tables()
        logger.info("Memory initialised at %s", self.db_path)

    # -----------------------------------------------------------------------
    def _create_tables(self) -> None:
        with self._lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_input TEXT,
                    response   TEXT,
                    action     TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            self.conn.commit()

    # -----------------------------------------------------------------------
    def add_conversation(self, user_input: str, response: str, action: str) -> None:
        """Encrypt and persist a conversation turn."""
        try:
            enc_input    = self.sec.encrypt(user_input).hex()
            enc_response = self.sec.encrypt(response).hex()
            with self._lock:
                self.conn.execute(
                    "INSERT INTO conversations (timestamp, user_input, response, action) "
                    "VALUES (?, ?, ?, ?)",
                    (datetime.now().isoformat(), enc_input, enc_response, action),
                )
                self.conn.commit()
        except Exception as e:
            logger.error("Memory.add_conversation error: %s", e)

    # -----------------------------------------------------------------------
    def get_recent_context(self, limit: int = 5) -> List[Dict[str, str]]:
        """Return last `limit` decrypted conversation pairs."""
        context: List[Dict[str, str]] = []
        try:
            with self._lock:
                cursor = self.conn.execute(
                    "SELECT user_input, response FROM conversations "
                    "ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                )
                rows = cursor.fetchall()

            for enc_input, enc_response in rows:
                try:
                    ui_bytes = bytes.fromhex(enc_input)  if enc_input  else b""
                    rp_bytes = bytes.fromhex(enc_response) if enc_response else b""
                    user = self.sec.decrypt(ui_bytes) if ui_bytes else ""
                    resp = self.sec.decrypt(rp_bytes) if rp_bytes else ""
                    context.append({"user": user, "assistant": resp})
                except Exception as e:
                    logger.warning("Memory decrypt error (skipping row): %s", e)

        except Exception as e:
            logger.error("Memory.get_recent_context error: %s", e)

        return context

    # -----------------------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        """Return memory stats for the dashboard."""
        try:
            with self._lock:
                total = self.conn.execute(
                    "SELECT COUNT(*) FROM conversations"
                ).fetchone()[0]
                last_ts = self.conn.execute(
                    "SELECT timestamp FROM conversations ORDER BY timestamp DESC LIMIT 1"
                ).fetchone()
            return {
                "total_conversations": total,
                "last_interaction":    last_ts[0] if last_ts else None,
                "db_path":             self.db_path,
            }
        except Exception as e:
            logger.error("Memory.get_stats error: %s", e)
            return {"total_conversations": 0, "last_interaction": None}
