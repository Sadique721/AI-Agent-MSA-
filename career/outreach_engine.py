"""
career/outreach_engine.py
=========================
Recruiter cold email and follow-up outreach compiler (V9).

Uses LLM to compile personalized email copy based on target company, role,
and recruiter contact names.
"""
from __future__ import annotations

import logging
from typing import Optional

from career.job_models import JobListing, RecruiterContact

logger = logging.getLogger("msa.career.outreach")


class OutreachEngine:
    """
    Formulates personalized communications for outreach campaigns.
    """

    def __init__(self, llm_manager=None) -> None:
        self._llm = llm_manager

    def compile_cold_email(
        self,
        contact: RecruiterContact,
        job: JobListing,
        llm_manager=None,
    ) -> str:
        """
        Generates a highly personalized cold email text.
        Falls back to a standard template if LLM is unavailable.
        """
        llm = llm_manager or self._llm

        if llm is None:
            return self._template_cold_email(contact, job)

        prompt = (
            f"Write a short, highly professional cold outreach email to a recruiter.\n\n"
            f"RECRUITER NAME: {contact.name}\n"
            f"RECRUITER COMPANY: {contact.company}\n"
            f"JOB DETAILS: {job.title} at {job.company}\n\n"
            f"Instructions:\n"
            f"  - Subject line should be punchy and clear\n"
            f"  - Length must be under 150 words\n"
            f"  - Reference the candidate's strong profile and interest in this role\n"
            f"  - Do not make up facts; refer to the resume attached (placeholder)\n"
            f"  - Output ONLY the email subject and body text, no conversational wrapper."
        )

        try:
            return llm.generate(prompt, max_tokens=300)
        except Exception as exc:
            logger.warning("[OutreachEngine] AI cold email compile failed: %s", exc)
            return self._template_cold_email(contact, job)

    def compile_followup(
        self,
        contact: RecruiterContact,
        days_since: int = 7,
        llm_manager=None,
    ) -> str:
        """Generates a brief follow-up email after a previous attempt."""
        llm = llm_manager or self._llm

        if llm is None:
            return (
                f"Subject: Follow-up regarding application at {contact.company}\n\n"
                f"Hi {contact.name},\n\n"
                f"I hope you are having a great week.\n\n"
                f"I wanted to follow up briefly regarding the application I submitted. "
                f"I remain very interested in the opportunities at {contact.company} "
                f"and would appreciate any update you might have.\n\n"
                f"Best regards,\nCandidate"
            )

        prompt = (
            f"Write a polite, professional follow-up email to a recruiter after {days_since} days.\n"
            f"Recruiter: {contact.name} at {contact.company}.\n"
            f"Keep it under 80 words. Be respectful of their time. "
            f"Output ONLY the subject and body."
        )
        try:
            return llm.generate(prompt, max_tokens=150)
        except Exception as exc:
            logger.warning("[OutreachEngine] AI follow-up compile failed: %s", exc)
            return f"Hi {contact.name}, just following up on my previous message. Let me know if you need anything else!"

    @staticmethod
    def _template_cold_email(contact: RecruiterContact, job: JobListing) -> str:
        """Structured outreach template fallback."""
        return (
            f"Subject: Inquiry: {job.title} opportunities at {contact.company}\n\n"
            f"Hi {contact.name},\n\n"
            f"I hope this email finds you well.\n\n"
            f"I recently came across the {job.title} opening at {contact.company} and "
            f"was thoroughly impressed by the team's work. With my background in software "
            f"development, I believe my skills align well with what you're looking for.\n\n"
            f"I've attached my resume for your review. I would welcome a brief call to "
            f"discuss how my background can support your goals.\n\n"
            f"Best regards,\nCandidate"
        )
