"""
career/application_engine.py
==============================
Autonomous Job Application Engine (V8).

Handles the full application lifecycle for all three strategies:
  1. easy_apply     — LinkedIn/Indeed 1-click via Playwright
  2. company_portal — Multi-step form fill via FormHandler
  3. manual         — Queues for user action (outreach or manual apply)

SAFETY:
  AUTO_APPLY_ENABLED = False by default in config.py.
  When False, the engine stages the application and emits a
  socketio "apply_confirmation_needed" event — the user must approve
  before any form is submitted.

Usage:
    from career.application_engine import ApplicationEngine
    engine = ApplicationEngine()
    result = engine.apply(job_listing, resume_text, cover_letter)
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Optional

from career.job_models import ApplicationRecord, JobListing
from config import (
    AUTO_APPLY_ENABLED, APPLICATIONS_DB, EVIDENCE_DIR,
    APPLICATION_RETRY_LIMIT, APPLICATION_RETRY_DELAY,
)

logger = logging.getLogger("msa.career.application")


class ApplicationEngine:
    """
    Orchestrates job applications using Playwright browser automation.
    """

    def __init__(self) -> None:
        os.makedirs(EVIDENCE_DIR, exist_ok=True)
        self._db = self._init_db()

    # ── Public API ────────────────────────────────────────────────────────────

    def apply(
        self,
        job: JobListing,
        resume_text: str = "",
        cover_letter: str = "",
        resume_path: Optional[str] = None,
        force: bool = False,
    ) -> ApplicationRecord:
        """
        Attempt to apply to a job.

        If AUTO_APPLY_ENABLED is False and force is False:
          - Creates a staged ApplicationRecord with status "queued"
          - Returns immediately (user must call confirm_and_apply later)

        If AUTO_APPLY_ENABLED is True or force=True:
          - Proceeds directly to submission
        """
        record = self._get_or_create_record(job)

        if not AUTO_APPLY_ENABLED and not force:
            record.status = "queued"
            record.notes = "Awaiting user confirmation before submission."
            self._save_record(record)
            logger.info("[AppEngine] Application queued (AUTO_APPLY_ENABLED=False): %s", job.id)
            self._notify_user_confirmation_needed(job, record)
            return record

        return self._execute_apply(job, record, resume_text, cover_letter, resume_path)

    def confirm_and_apply(
        self,
        job_id: str,
        resume_text: str = "",
        cover_letter: str = "",
        resume_path: Optional[str] = None,
    ) -> Optional[ApplicationRecord]:
        """Called after user approves a queued application."""
        record = self._load_record(job_id)
        if record is None:
            logger.warning("[AppEngine] No queued record found for job %s", job_id)
            return None
        # We need the job listing — load from any context available
        job = JobListing(
            title="", company="", location="", url="", source="",
            id=job_id,
        )
        return self._execute_apply(job, record, resume_text, cover_letter, resume_path)

    # ── Application Execution ─────────────────────────────────────────────────

    def _execute_apply(
        self,
        job: JobListing,
        record: ApplicationRecord,
        resume_text: str,
        cover_letter: str,
        resume_path: Optional[str],
    ) -> ApplicationRecord:
        """Core application execution with retry and recovery."""
        from career.recovery_engine import RecoveryEngine
        recovery = RecoveryEngine()

        for attempt in range(1, APPLICATION_RETRY_LIMIT + 1):
            try:
                recovery.checkpoint(job.id, f"attempt_{attempt}", {"attempt": attempt})
                logger.info("[AppEngine] Applying to %s @ %s (attempt %d)", job.title, job.company, attempt)

                if job.apply_type == "easy_apply":
                    success = self._apply_easy_apply(job, resume_text, cover_letter, resume_path, record)
                else:
                    success = self._apply_company_portal(job, resume_text, cover_letter, resume_path, record)

                if success:
                    record.status = "applied"
                    record.applied_at = datetime.utcnow().isoformat()
                    self._save_record(record)
                    logger.info("[AppEngine] Successfully applied to %s @ %s", job.title, job.company)
                    return record

            except Exception as exc:
                logger.warning("[AppEngine] Attempt %d failed for %s: %s", attempt, job.id, exc)
                record.notes += f"\n[attempt {attempt}] {exc}"
                if attempt < APPLICATION_RETRY_LIMIT:
                    delay = APPLICATION_RETRY_DELAY * (2 ** (attempt - 1))
                    logger.info("[AppEngine] Retrying in %ds...", delay)
                    time.sleep(delay)

        # All retries exhausted
        record.status = "failed"
        recovery.mark_failed(job.id, "Max retries exceeded")
        self._save_record(record)
        logger.error("[AppEngine] All %d attempts failed for %s", APPLICATION_RETRY_LIMIT, job.id)
        return record

    # ── Easy Apply (LinkedIn / Indeed) ────────────────────────────────────────

    def _apply_easy_apply(
        self, job: JobListing, resume_text: str, cover_letter: str,
        resume_path: Optional[str], record: ApplicationRecord,
    ) -> bool:
        """LinkedIn Easy Apply / Indeed quick-apply flow."""
        try:
            from browser_agent.browser_controller import controller
            from career.form_handler import FormHandler
            page = controller.get_page()

            logger.info("[AppEngine] Navigating to Easy Apply: %s", job.url)
            page.goto(job.url, timeout=30000)
            page.wait_for_timeout(2000)

            # Screenshot pre-submit
            screenshot = self._save_screenshot(job.id, "pre_apply")
            record.screenshots.append(screenshot)

            # Click the Apply / Easy Apply button
            for btn_text in ["Easy Apply", "Apply Now", "Apply", "Quick Apply"]:
                try:
                    btn = page.get_by_role("button", name=btn_text, exact=False).first
                    if btn.count() > 0:
                        btn.click()
                        page.wait_for_timeout(1500)
                        break
                except Exception:
                    continue

            # Fill the form
            handler = FormHandler()
            form_data = self._build_form_data(resume_text, cover_letter)
            handler.fill_standard_fields(page, form_data)

            if resume_path and os.path.exists(resume_path):
                handler.upload_file(page, resume_path, field_label="resume")

            # Submit
            page.wait_for_timeout(1000)
            confirmed = self._confirm_submission(page)

            if confirmed:
                screenshot_post = self._save_screenshot(job.id, "post_apply")
                record.screenshots.append(screenshot_post)

            return confirmed

        except Exception as exc:
            logger.error("[AppEngine] Easy Apply failed: %s", exc)
            return False

    # ── Company Portal Apply ──────────────────────────────────────────────────

    def _apply_company_portal(
        self, job: JobListing, resume_text: str, cover_letter: str,
        resume_path: Optional[str], record: ApplicationRecord,
    ) -> bool:
        """Multi-step company careers portal application."""
        try:
            from browser_agent.browser_controller import controller
            from career.form_handler import FormHandler
            page = controller.get_page()

            logger.info("[AppEngine] Navigating to portal: %s", job.url)
            page.goto(job.url, timeout=30000)
            page.wait_for_timeout(2500)

            screenshot = self._save_screenshot(job.id, "portal_loaded")
            record.screenshots.append(screenshot)

            handler = FormHandler()
            form_data = self._build_form_data(resume_text, cover_letter)

            # Detect and fill form fields
            handler.fill_standard_fields(page, form_data)

            if resume_path and os.path.exists(resume_path):
                handler.upload_file(page, resume_path, field_label="resume")

            if cover_letter:
                handler.fill_text_area(page, "cover letter", cover_letter)

            # Try to submit
            for submit_text in ["Submit Application", "Submit", "Apply", "Send Application"]:
                try:
                    btn = page.get_by_role("button", name=submit_text, exact=False).first
                    if btn.count() > 0:
                        btn.click()
                        page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

            confirmed = self._confirm_submission(page)
            if confirmed:
                post_shot = self._save_screenshot(job.id, "portal_submitted")
                record.screenshots.append(post_shot)

            return confirmed

        except Exception as exc:
            logger.error("[AppEngine] Portal apply failed: %s", exc)
            return False

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _confirm_submission(self, page) -> bool:
        """Detect successful submission by checking for confirmation text."""
        page.wait_for_timeout(2000)
        try:
            body_text = page.locator("body").inner_text(timeout=5000).lower()
            confirmation_signals = [
                "application submitted", "successfully applied",
                "thank you for applying", "your application has been",
                "application received", "we'll be in touch",
            ]
            return any(sig in body_text for sig in confirmation_signals)
        except Exception:
            return False

    def _save_screenshot(self, job_id: str, label: str) -> str:
        """Save an evidence screenshot and return the path."""
        try:
            from browser_agent.browser_controller import controller
            job_dir = os.path.join(EVIDENCE_DIR, job_id)
            os.makedirs(job_dir, exist_ok=True)
            ts = int(time.time())
            path = os.path.join(job_dir, f"{label}_{ts}.png")
            page = controller.get_page()
            page.screenshot(path=path)
            return path
        except Exception as exc:
            logger.debug("[AppEngine] Screenshot failed: %s", exc)
            return ""

    @staticmethod
    def _build_form_data(resume_text: str, cover_letter: str) -> dict:
        """Build standard field map from user profile + resume."""
        from config import USER_PROFILE
        return {
            "name":         USER_PROFILE.get("name", ""),
            "email":        USER_PROFILE.get("email", ""),
            "phone":        USER_PROFILE.get("phone", ""),
            "resume_text":  resume_text,
            "cover_letter": cover_letter,
        }

    def _notify_user_confirmation_needed(self, job: JobListing, record: ApplicationRecord) -> None:
        """Push a socketio event so the frontend can prompt the user."""
        try:
            from backend.server import socketio
            socketio.emit("apply_confirmation_needed", {
                "job_id":    job.id,
                "job_title": job.title,
                "company":   job.company,
                "url":       job.url,
                "record_id": record.job_id,
            })
        except Exception:
            pass  # Frontend notification is non-critical

    # ── Persistence ───────────────────────────────────────────────────────────

    def _init_db(self):
        """Lazy import to avoid circular dependencies at module load."""
        import sqlite3
        conn = sqlite3.connect(APPLICATIONS_DB)
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
        conn.commit()
        return conn

    def _save_record(self, record: ApplicationRecord) -> None:
        import json
        try:
            self._db.execute("""
                INSERT OR REPLACE INTO applications VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                record.job_id, record.status, record.applied_at,
                record.cover_letter_version, record.resume_version,
                json.dumps(record.screenshots), record.notes,
                record.follow_up_date, record.rejection_reason, record.interview_date,
            ))
            self._db.commit()
        except Exception as exc:
            logger.error("[AppEngine] DB save failed: %s", exc)

    def _load_record(self, job_id: str) -> Optional[ApplicationRecord]:
        import json
        try:
            row = self._db.execute(
                "SELECT * FROM applications WHERE job_id=?", (job_id,)
            ).fetchone()
            if row:
                return ApplicationRecord(
                    job_id=row[0], status=row[1], applied_at=row[2],
                    cover_letter_version=row[3], resume_version=row[4],
                    screenshots=json.loads(row[5] or "[]"),
                    notes=row[6] or "", follow_up_date=row[7],
                    rejection_reason=row[8], interview_date=row[9],
                )
        except Exception as exc:
            logger.error("[AppEngine] DB load failed: %s", exc)
        return None

    def _get_or_create_record(self, job: JobListing) -> ApplicationRecord:
        record = self._load_record(job.id)
        if record is None:
            record = ApplicationRecord(job_id=job.id)
        return record
