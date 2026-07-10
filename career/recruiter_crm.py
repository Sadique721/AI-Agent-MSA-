"""
career/recruiter_crm.py
=======================
Recruiter CRM & Contact Management Database (V9).

Tracks hiring managers, recruiters, cold emails, response histories,
and automatically highlights upcoming or overdue follow-ups.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from career.job_models import RecruiterContact
from config import RECRUITER_CRM_DB

logger = logging.getLogger("msa.career.crm")


class RecruiterCRM:
    """
    SQLite-backed contact log and follow-up CRM.
    """

    def __init__(self) -> None:
        self._db = self._init_db()

    def add_contact(self, contact: RecruiterContact) -> None:
        """Saves a new recruiter contact."""
        try:
            now = datetime.now(timezone.utc).isoformat()
            self._db.execute("""
                INSERT OR REPLACE INTO contacts (id, name, company, email, linkedin_url, phone, notes, added_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                contact.id, contact.name, contact.company, contact.email,
                contact.linkedin_url, contact.phone, contact.notes,
                contact.added_at or now
            ))
            self._db.commit()
            logger.info("[CRM] Contact added: %s (%s)", contact.name, contact.company)
        except Exception as exc:
            logger.error("[CRM] Add contact failed: %s", exc)

    def get_contact(self, contact_id: str) -> Optional[RecruiterContact]:
        """Loads a contact from DB."""
        try:
            row = self._db.execute("SELECT * FROM contacts WHERE id=?", (contact_id,)).fetchone()
            if row:
                return RecruiterContact(
                    id=row[0], name=row[1], company=row[2], email=row[3],
                    linkedin_url=row[4], phone=row[5], notes=row[6],
                    added_at=row[7], last_contacted=row[8],
                )
        except Exception as exc:
            logger.error("[CRM] Get contact failed: %s", exc)
        return None

    def list_contacts(self) -> List[RecruiterContact]:
        """Returns all contacts."""
        contacts = []
        try:
            rows = self._db.execute("SELECT * FROM contacts").fetchall()
            for r in rows:
                contacts.append(RecruiterContact(
                    id=r[0], name=r[1], company=r[2], email=r[3],
                    linkedin_url=r[4], phone=r[5], notes=r[6],
                    added_at=r[7], last_contacted=r[8],
                ))
        except Exception as exc:
            logger.error("[CRM] List contacts failed: %s", exc)
        return contacts

    def log_outreach(self, contact_id: str, channel: str, message: str) -> None:
        """Records an outreach attempt (email, LinkedIn message, etc.)."""
        try:
            now = datetime.now(timezone.utc).isoformat()
            self._db.execute("""
                INSERT INTO outreach_log (contact_id, channel, message, sent_at)
                VALUES (?, ?, ?, ?)
            """, (contact_id, channel, message, now))
            
            # Update last contacted time in contact table
            self._db.execute(
                "UPDATE contacts SET last_contacted=? WHERE id=?", (now, contact_id)
            )
            self._db.commit()
            logger.info("[CRM] Logged outreach attempt to contact: %s", contact_id)
        except Exception as exc:
            logger.error("[CRM] Log outreach failed: %s", exc)

    def log_response(self, contact_id: str, message: str) -> None:
        """Records a response message received from a recruiter."""
        try:
            now = datetime.now(timezone.utc).isoformat()
            self._db.execute("""
                INSERT INTO responses (contact_id, message, received_at)
                VALUES (?, ?, ?)
            """, (contact_id, message, now))
            self._db.commit()
            logger.info("[CRM] Logged response from contact: %s", contact_id)
        except Exception as exc:
            logger.error("[CRM] Log response failed: %s", exc)

    def schedule_followup(self, contact_id: str, date_str: str, template: str = "") -> None:
        """Schedules a future follow-up outreach task."""
        try:
            self._db.execute("""
                INSERT OR REPLACE INTO follow_ups (contact_id, follow_up_date, template, completed)
                VALUES (?, ?, ?, 0)
            """, (contact_id, date_str, template))
            self._db.commit()
            logger.info("[CRM] Scheduled follow-up on %s for contact: %s", date_str, contact_id)
        except Exception as exc:
            logger.error("[CRM] Schedule follow-up failed: %s", exc)

    def get_pending_followups(self) -> List[Dict[str, Any]]:
        """Returns all follow-ups scheduled for today or earlier that are not completed."""
        results = []
        try:
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            query = """
                SELECT f.contact_id, c.name, c.company, c.email, f.follow_up_date, f.template
                FROM follow_ups f
                JOIN contacts c ON f.contact_id = c.id
                WHERE f.follow_up_date <= ? AND f.completed = 0
            """
            rows = self._db.execute(query, (now_str,)).fetchall()
            for r in rows:
                results.append({
                    "contact_id": r[0],
                    "name": r[1],
                    "company": r[2],
                    "email": r[3],
                    "date": r[4],
                    "template": r[5],
                })
        except Exception as exc:
            logger.error("[CRM] Pending followups query failed: %s", exc)
        return results

    def mark_followup_completed(self, contact_id: str) -> None:
        """Marks a follow-up task as done."""
        try:
            self._db.execute(
                "UPDATE follow_ups SET completed = 1 WHERE contact_id = ?", (contact_id,)
            )
            self._db.commit()
        except Exception as exc:
            logger.error("[CRM] Mark completed failed: %s", exc)

    # ── Database Init ─────────────────────────────────────────────────────────

    def _init_db(self):
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
                channel TEXT, -- email | linkedin | phone
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
                follow_up_date TEXT, -- YYYY-MM-DD
                template TEXT,
                completed INTEGER,
                FOREIGN KEY(contact_id) REFERENCES contacts(id)
            )
        """)
        conn.commit()
        return conn
