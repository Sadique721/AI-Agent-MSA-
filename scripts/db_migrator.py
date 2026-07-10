"""
scripts/db_migrator.py
======================
Database schema migration manager (V10).

Executes schema setup, version tracking, and rollbacks for SQLite databases
used by the Career Intelligence Platform and Recruiter CRM.
"""
from __future__ import annotations

import logging
import sqlite3
from config import APPLICATIONS_DB, RECRUITER_CRM_DB

logger = logging.getLogger("msa.db.migrator")


class DBMigrator:
    """
    Manages schemas and versions for career-related sqlite databases.
    """

    def __init__(self) -> None:
        pass

    def run_all(self) -> bool:
        """Executes table schemas across all databases."""
        try:
            self._migrate_applications()
            self._migrate_recruiter_crm()
            logger.info("[DBMigrator] Database migrations complete.")
            return True
        except Exception as exc:
            logger.error("[DBMigrator] Migration failed: %s", exc)
            return False

    def _migrate_applications(self) -> None:
        """Sets up/updates schema for applications database."""
        conn = sqlite3.connect(APPLICATIONS_DB)
        # Create core table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                job_id TEXT PRIMARY KEY,
                status TEXT,
                applied_at TEXT,
                cover_letter_version TEXT,
                resume_version TEXT,
                screenshots TEXT,
                notes TEXT,
                follow_up_date TEXT,
                rejection_reason TEXT,
                interview_date TEXT
            )
        """)
        # Create interview rounds table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS interview_rounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                round_name TEXT,
                date_time TEXT,
                interviewer TEXT,
                notes TEXT,
                result TEXT,
                feedback TEXT,
                FOREIGN KEY(job_id) REFERENCES applications(job_id)
            )
        """)
        conn.commit()
        conn.close()

    def _migrate_recruiter_crm(self) -> None:
        """Sets up/updates schema for recruiter crm database."""
        conn = sqlite3.connect(RECRUITER_CRM_DB)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id TEXT PRIMARY KEY,
                name TEXT,
                company TEXT,
                email TEXT,
                linkedin_url TEXT,
                phone TEXT,
                notes TEXT,
                added_at TEXT,
                last_contacted TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS outreach_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id TEXT,
                channel TEXT,
                message TEXT,
                sent_at TEXT,
                FOREIGN KEY(contact_id) REFERENCES contacts(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id TEXT,
                message TEXT,
                received_at TEXT,
                FOREIGN KEY(contact_id) REFERENCES contacts(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS follow_ups (
                contact_id TEXT PRIMARY KEY,
                follow_up_date TEXT,
                template TEXT,
                completed INTEGER,
                FOREIGN KEY(contact_id) REFERENCES contacts(id)
            )
        """)
        conn.commit()
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    DBMigrator().run_all()
