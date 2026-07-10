"""
career/application_strategy.py
================================
Application Strategy Router (V7).

Classifies each JobListing into one of three apply strategies:
  - "easy_apply"         — LinkedIn Easy Apply / Indeed One-Click (browser automation)
  - "company_portal"     — Company careers page (multi-step form)
  - "recruiter_outreach" — No online form found; requires direct recruiter contact

Usage:
    from career.application_strategy import ApplicationStrategyRouter
    router = ApplicationStrategyRouter()
    strategy = router.classify(job_listing)
"""
from __future__ import annotations

import logging
import re
from typing import List

from career.job_models import JobListing

logger = logging.getLogger("msa.career.strategy")

# ── URL patterns that indicate a company's own career portal ─────────────────
_COMPANY_PORTAL_DOMAINS = re.compile(
    r"(greenhouse\.io|lever\.co|workday\.com|icims\.com|taleo\.net"
    r"|smartrecruiters\.com|recruitee\.com|breezy\.hr|myworkdayjobs\.com"
    r"|careers\.\w+\.\w+|jobs\.\w+\.\w+)",
    re.I,
)

# Easy apply indicators in the job listing
_EASY_APPLY_SIGNALS = [
    "easy apply", "1-click apply", "quick apply", "apply now",
    "linkedin.com/jobs", "indeed.com/applystart",
]

# Signals that no online form exists → recruiter outreach needed
_OUTREACH_SIGNALS = [
    "send your resume to", "email us at", "contact us",
    "send cv to", "reach out to", "dm us",
]


class ApplicationStrategyRouter:
    """
    Classifies a JobListing into apply strategy and updates job.apply_type.
    """

    def classify(self, job: JobListing) -> str:
        """
        Returns "easy_apply" | "company_portal" | "recruiter_outreach"
        and updates job.apply_type in-place.
        """
        strategy = self._detect_strategy(job)
        job.apply_type = strategy
        logger.debug("[Strategy] %s @ %s → %s", job.title, job.company, strategy)
        return strategy

    def classify_batch(self, jobs: List[JobListing]) -> List[JobListing]:
        """Classify a list of jobs and return them with apply_type set."""
        for job in jobs:
            self.classify(job)
        return jobs

    def _detect_strategy(self, job: JobListing) -> str:
        """Core classification logic."""
        desc_lower = (job.description + " " + job.url).lower()
        url_lower = job.url.lower()

        # 1. Source-level signals (highest confidence)
        if job.source == "linkedin":
            # Check if LinkedIn shows the Easy Apply badge
            if "easyapply" in url_lower or "easy apply" in desc_lower:
                return "easy_apply"
            # LinkedIn jobs without Easy Apply go to company portal
            return "company_portal"

        if job.source == "indeed":
            if "applystart" in url_lower or "quick apply" in desc_lower:
                return "easy_apply"
            return "company_portal"

        # 2. URL domain analysis
        if _COMPANY_PORTAL_DOMAINS.search(url_lower):
            return "company_portal"

        # 3. Description signals
        for signal in _EASY_APPLY_SIGNALS:
            if signal in desc_lower:
                return "easy_apply"

        for signal in _OUTREACH_SIGNALS:
            if signal in desc_lower:
                return "recruiter_outreach"

        # 4. Email found but no application URL → outreach
        if re.search(r"\b[\w.+-]+@[\w-]+\.\w{2,}\b", job.description) and not job.url:
            return "recruiter_outreach"

        # 5. Default: company portal (safest fallback)
        return "company_portal"

    def get_priority_queue(self, jobs: List[JobListing]) -> dict:
        """
        Segment classified jobs by strategy for ordered processing.
        Returns dict with keys: easy_apply, company_portal, recruiter_outreach.
        """
        self.classify_batch(jobs)
        return {
            "easy_apply":         [j for j in jobs if j.apply_type == "easy_apply"],
            "company_portal":     [j for j in jobs if j.apply_type == "company_portal"],
            "recruiter_outreach": [j for j in jobs if j.apply_type == "recruiter_outreach"],
        }

    def summary(self, jobs: List[JobListing]) -> str:
        """Return a human-readable strategy summary."""
        queue = self.get_priority_queue(jobs)
        return (
            f"Strategy breakdown ({len(jobs)} jobs):\n"
            f"  Easy Apply:         {len(queue['easy_apply'])} jobs\n"
            f"  Company Portal:     {len(queue['company_portal'])} jobs\n"
            f"  Recruiter Outreach: {len(queue['recruiter_outreach'])} jobs"
        )
