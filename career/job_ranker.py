"""
career/job_ranker.py
====================
Job deduplication, ranking, and filtering (V7).

Ranking formula (weighted score 0.0 - 1.0):
  40% — ATS score        (keyword density match vs master resume)
  40% — match_score      (semantic cosine similarity vs master resume embedding)
  20% — recency bonus    (newer postings ranked slightly higher)

Usage:
    from career.job_ranker import JobRanker
    ranker = JobRanker(user_skills=["Python", "React", "Docker"])
    ranked = ranker.rank(job_listings, resume_text=resume)
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import List, Optional, Set

from career.job_models import JobListing
from config import ATS_SCORE_THRESHOLD, MATCH_SCORE_THRESHOLD, COMPANY_BLACKLIST

logger = logging.getLogger("msa.career.ranker")


class JobRanker:
    """
    Deduplicates, filters, and ranks job listings.
    All operations are purely in-memory and side-effect free.
    """

    def __init__(self, user_skills: Optional[List[str]] = None) -> None:
        from config import USER_PROFILE
        self._skills: Set[str] = {
            s.lower() for s in (user_skills or USER_PROFILE.get("skills", []))
        }
        self._blacklist: Set[str] = {c.lower() for c in (COMPANY_BLACKLIST or [])}

    # ── Public API ────────────────────────────────────────────────────────────

    def rank(
        self,
        listings: List[JobListing],
        resume_text: str = "",
        min_ats: float = ATS_SCORE_THRESHOLD,
        min_match: float = MATCH_SCORE_THRESHOLD,
    ) -> List[JobListing]:
        """
        Score, filter, and sort listings.
        Returns list ordered by composite score descending.
        """
        deduplicated = self.deduplicate(listings)
        filtered = self.filter_by_blacklist(deduplicated)

        for job in filtered:
            if resume_text:
                job.ats_score = self._quick_ats_score(job.description, resume_text)
                job.match_score = self._quick_match_score(job.title + " " + job.description, resume_text)

        qualifying = [
            j for j in filtered
            if j.ats_score >= min_ats or j.match_score >= min_match
            or (j.ats_score == 0.0 and j.match_score == 0.0)  # unscoredpass-through
        ]

        qualifying.sort(key=lambda j: self._composite(j), reverse=True)
        logger.info("[Ranker] %d → %d after dedup/filter/rank", len(listings), len(qualifying))
        return qualifying

    def deduplicate(self, listings: List[JobListing]) -> List[JobListing]:
        """Remove duplicate listings by SHA-256 id fingerprint."""
        seen: Set[str] = set()
        unique = []
        for job in listings:
            if job.id not in seen:
                seen.add(job.id)
                unique.append(job)
        logger.debug("[Ranker] Dedup: %d → %d", len(listings), len(unique))
        return unique

    def filter_by_skills(
        self, listings: List[JobListing], min_skill_overlap: int = 1
    ) -> List[JobListing]:
        """Keep only listings whose description mentions at least N user skills."""
        if not self._skills:
            return listings
        result = []
        for job in listings:
            desc_lower = (job.title + " " + job.description).lower()
            overlap = sum(1 for s in self._skills if s in desc_lower)
            if overlap >= min_skill_overlap:
                result.append(job)
        return result

    def filter_by_location(
        self, listings: List[JobListing], preferred_locations: List[str]
    ) -> List[JobListing]:
        """Keep only listings matching any of the preferred locations (case-insensitive substring)."""
        if not preferred_locations:
            return listings
        prefs = [p.lower() for p in preferred_locations]
        return [
            j for j in listings
            if any(p in j.location.lower() for p in prefs)
            or "remote" in j.location.lower()
            or not j.location.strip()  # unknown location — keep
        ]

    def filter_by_blacklist(self, listings: List[JobListing]) -> List[JobListing]:
        """Remove listings from blacklisted companies."""
        if not self._blacklist:
            return listings
        return [j for j in listings if j.company.lower() not in self._blacklist]

    # ── Scoring helpers ───────────────────────────────────────────────────────

    def _quick_ats_score(self, job_desc: str, resume: str) -> float:
        """
        Fast keyword-overlap ATS score — does NOT need sentence-transformers.
        Used as a lightweight pre-filter before the heavy ResumeMatcher runs.
        """
        if not job_desc or not resume:
            return 0.0
        desc_tokens = set(re.findall(r"\b\w{3,}\b", job_desc.lower()))
        resume_tokens = set(re.findall(r"\b\w{3,}\b", resume.lower()))
        if not desc_tokens:
            return 0.0
        overlap = desc_tokens & resume_tokens
        # Weight: skill words count double
        skill_bonus = sum(2 for t in overlap if t in self._skills)
        raw = (len(overlap) + skill_bonus) / (len(desc_tokens) + 1e-9)
        return min(round(float(raw), 4), 1.0)

    def _quick_match_score(self, text: str, resume: str) -> float:
        """
        Very lightweight Jaccard similarity used for initial ranking.
        ResumeMatcher will replace this with a proper cosine embedding score.
        """
        if not text or not resume:
            return 0.0
        a = set(re.findall(r"\b\w{4,}\b", text.lower()))
        b = set(re.findall(r"\b\w{4,}\b", resume.lower()))
        intersection = a & b
        union = a | b
        if not union:
            return 0.0
        return round(len(intersection) / len(union), 4)

    @staticmethod
    def _recency_bonus(job: JobListing) -> float:
        """0.0-0.1 bonus for jobs posted within the last 7 days."""
        if not job.posted_date:
            return 0.0
        try:
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d %b %Y"):
                try:
                    posted = datetime.strptime(job.posted_date[:10], fmt[:len(job.posted_date[:10])])
                    days_old = (datetime.utcnow() - posted).days
                    return max(0.0, 0.1 - days_old * 0.014)
                except ValueError:
                    continue
        except Exception:
            pass
        return 0.0

    def _composite(self, job: JobListing) -> float:
        """Weighted composite score: 40% ATS + 40% match + 20% recency."""
        return (
            0.40 * job.ats_score
            + 0.40 * job.match_score
            + 0.20 * self._recency_bonus(job)
        )
