"""
career/job_models.py
====================
Core data models for the Career Intelligence Platform (V7).
All career data flows through these dataclasses — keeping a single
canonical shape makes deduplication, ranking, and storage uniform.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional


# ── JobListing ────────────────────────────────────────────────────────────────

@dataclass
class JobListing:
    """
    A single normalised job posting from any source.

    id  — SHA-256 fingerprint of (title + company + url) used for deduplication.
    apply_type — "easy_apply" | "company_portal" | "recruiter_outreach"
    ats_score  — 0.0-1.0 after ResumeMatcher runs; 0.0 until scored.
    match_score— 0.0-1.0 semantic similarity to master resume; 0.0 until scored.
    """
    title: str
    company: str
    location: str
    url: str
    source: str                         # linkedin | indeed | naukri | adzuna | jooble | company
    description: str = ""
    salary_range: Optional[str] = None
    job_type: Optional[str] = None      # full-time | contract | remote | hybrid | internship
    posted_date: Optional[str] = None
    apply_type: str = "company_portal"  # overwritten by ApplicationStrategyRouter
    ats_score: float = 0.0
    match_score: float = 0.0
    raw_html: str = ""
    id: str = field(default="")         # computed on __post_init__

    def __post_init__(self):
        if not self.id:
            fingerprint = f"{self.title.lower()}|{self.company.lower()}|{self.url}"
            self.id = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "JobListing":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def short_summary(self) -> str:
        return (
            f"[{self.source.upper()}] {self.title} @ {self.company} "
            f"({self.location}) — ATS:{self.ats_score:.2f} Match:{self.match_score:.2f}"
        )


# ── ApplicationRecord ─────────────────────────────────────────────────────────

@dataclass
class ApplicationRecord:
    """
    Tracks the full lifecycle of a single job application.

    status progression:
        discovered → queued → applied → rejected | interview | offer
    """
    job_id: str
    status: str = "discovered"          # discovered|queued|applied|rejected|interview|offer
    applied_at: Optional[str] = None
    cover_letter_version: str = ""
    resume_version: str = ""
    screenshots: List[str] = field(default_factory=list)
    notes: str = ""
    follow_up_date: Optional[str] = None
    rejection_reason: Optional[str] = None
    interview_date: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ApplicationRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── RecruiterContact ──────────────────────────────────────────────────────────

@dataclass
class RecruiterContact:
    """A recruiter or hiring manager contact record for the CRM."""
    name: str
    company: str
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    notes: str = ""
    added_at: Optional[str] = None
    last_contacted: Optional[str] = None
    id: str = field(default="")

    def __post_init__(self):
        if not self.id:
            fingerprint = f"{self.name.lower()}|{self.company.lower()}"
            self.id = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:12]


# ── ResumeVersion ─────────────────────────────────────────────────────────────

@dataclass
class ResumeVersion:
    """A single versioned snapshot of a resume."""
    version_id: str
    label: str              # "master" | "ats" | "targeted_<company>" | "cover_letter"
    content: str            # plain text or markdown
    job_id: Optional[str] = None
    created_at: Optional[str] = None
    ats_score: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)
