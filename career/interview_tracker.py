"""
career/interview_tracker.py
===========================
SQLite-backed interview stage logger and prep sheet generator (V9).

Logs upcoming interview rounds, aggregates outcome feedback, and employs
the core LLM manager to generate custom interview preparation sheets.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import APPLICATIONS_DB

logger = logging.getLogger("msa.career.interview")


class InterviewTracker:
    """
    Manages interview rounds and leverages AI to compile interview prep guidelines.
    """

    def __init__(self) -> None:
        self._db = self._init_db()

    def log_round(
        self,
        job_id: str,
        round_name: str,
        date_str: str,
        interviewer: str = "",
        notes: str = "",
    ) -> None:
        """Logs an upcoming interview round."""
        try:
            self._db.execute("""
                INSERT INTO interview_rounds (job_id, round_name, date_time, interviewer, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (job_id, round_name, date_str, interviewer, notes))
            
            # Update application status in core applications DB
            self._db.execute(
                "UPDATE applications SET status='interview', interview_date=? WHERE job_id=?",
                (date_str, job_id)
            )
            self._db.commit()
            logger.info("[InterviewTracker] Logged %s for job: %s", round_name, job_id)
        except Exception as exc:
            logger.error("[InterviewTracker] Log round failed: %s", exc)

    def log_feedback(self, round_id: int, result: str, feedback: str = "") -> None:
        """Saves outcome and feedback for an completed round."""
        try:
            self._db.execute("""
                UPDATE interview_rounds
                SET result=?, feedback=?
                WHERE id=?
            """, (result, feedback, round_id))
            self._db.commit()
            logger.info("[InterviewTracker] Logged feedback for round: %d", round_id)
        except Exception as exc:
            logger.error("[InterviewTracker] Log feedback failed: %s", exc)

    def get_rounds(self, job_id: str) -> List[Dict[str, Any]]:
        """Returns all rounds logged for a job."""
        results = []
        try:
            rows = self._db.execute(
                "SELECT id, round_name, date_time, interviewer, notes, result, feedback "
                "FROM interview_rounds WHERE job_id=?", (job_id,)
            ).fetchall()
            for r in rows:
                results.append({
                    "id": r[0], "round_name": r[1], "date_time": r[2],
                    "interviewer": r[3], "notes": r[4], "result": r[5], "feedback": r[6],
                })
        except Exception as exc:
            logger.error("[InterviewTracker] Get rounds failed: %s", exc)
        return results

    def get_upcoming_interviews(self) -> List[Dict[str, Any]]:
        """Returns rounds scheduled in the future."""
        results = []
        try:
            now_str = datetime.utcnow().isoformat()
            query = """
                SELECT r.id, r.job_id, r.round_name, r.date_time, r.interviewer
                FROM interview_rounds r
                WHERE r.date_time >= ? AND (r.result IS NULL OR r.result = '')
            """
            rows = self._db.execute(query, (now_str,)).fetchall()
            for r in rows:
                results.append({
                    "id": r[0], "job_id": r[1], "round_name": r[2], "date_time": r[3], "interviewer": r[4]
                })
        except Exception as exc:
            logger.error("[InterviewTracker] Get upcoming interviews failed: %s", exc)
        return results

    def generate_prep_sheet(self, job_id: str, job_desc: str, llm_manager) -> str:
        """
        Uses LLM to compile a custom interview cheat-sheet.
        Includes common technical/behavioral questions and best answers.
        """
        if not llm_manager:
            return "No LLM engine available to generate prep materials."

        prompt = (
            f"You are an expert interview coach. Compile a detailed, comprehensive "
            f"Interview Preparation Sheet for this job posting:\n\n"
            f"JOB DESCRIPTION:\n{job_desc[:1200]}\n\n"
            f"Structure the response with sections:\n"
            f"  1. Key Skills & Concepts to Review\n"
            f"  2. Expected Core Technical Questions (with brief guideline answers)\n"
            f"  3. Standard Behavioral Questions Tailored to Role (using STAR method guidelines)\n"
            f"  4. Questions Candidate Should Ask Interviewer\n"
            f"Maintain a supportive, clear tone. Output clean Markdown only."
        )
        try:
            return llm_manager.generate(prompt, max_tokens=1000)
        except Exception as exc:
            logger.warning("[InterviewTracker] AI prep sheet generation failed: %s", exc)
            return "Failed to compile prep sheet via AI."

    # ── Database Init ─────────────────────────────────────────────────────────

    def _init_db(self):
        # We reuse the core APPLICATIONS_DB connection
        conn = sqlite3.connect(APPLICATIONS_DB)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS interview_rounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                round_name TEXT, -- tech_phone | coding | system_design | behavioral | manager
                date_time TEXT,
                interviewer TEXT,
                notes TEXT,
                result TEXT, -- pass | fail | pending
                feedback TEXT,
                FOREIGN KEY(job_id) REFERENCES applications(job_id)
            )
        """)
        conn.commit()
        return conn
