"""
tests/test_career_v7.py
=======================
Unit tests for Phase 2 (V7 Career Intelligence) modules:
  - JobListing & ApplicationRecord model structures
  - JobRanker keyword density filtering & blacklisting
  - ResumeMatcher ATS scoring
  - ResumeEngine cover-letter compiling & targeted resume generation
"""
import os
import shutil
import pytest
from career.job_models import JobListing, ApplicationRecord, RecruiterContact
from career.job_ranker import JobRanker
from career.resume_matcher import ResumeMatcher
from career.resume_engine import ResumeEngine


@pytest.fixture()
def tmp_resume_dir(tmp_path):
    """Isolated resume dir per test — avoids PermissionError on shared directories."""
    import career.resume_engine as re_mod
    original = re_mod.RESUME_DIR if hasattr(re_mod, "RESUME_DIR") else None
    resume_dir = str(tmp_path / "resumes")
    os.makedirs(resume_dir, exist_ok=True)
    # Patch at module-level so ResumeEngine picks it up
    import config
    orig_cfg = config.RESUME_DIR
    config.RESUME_DIR = resume_dir
    yield resume_dir
    config.RESUME_DIR = orig_cfg


def test_job_listing_model():
    """Verify JobListing auto-computes unique SHA-256 id fingerprint."""
    job = JobListing(
        title="Python Engineer",
        company="Google",
        location="Bangalore",
        url="https://careers.google.com/jobs/123",
        source="company",
    )
    assert len(job.id) == 16
    assert job.apply_type == "company_portal"
    assert job.ats_score == 0.0


def test_job_listing_dedup_via_id():
    """Two identical jobs produce same fingerprint; two different jobs differ."""
    j1 = JobListing(title="Dev", company="A", location="X", url="http://u", source="s")
    j2 = JobListing(title="Dev", company="A", location="X", url="http://u", source="s")
    j3 = JobListing(title="Dev", company="B", location="X", url="http://u", source="s")
    assert j1.id == j2.id
    assert j1.id != j3.id


def test_job_ranker_blacklist_filtering():
    """Verify JobRanker removes blacklisted companies."""
    ranker = JobRanker(user_skills=["Python", "React"])
    ranker._blacklist = {"blacklistedcorp"}

    jobs = [
        JobListing(title="Dev", company="Apple", location="Remote", url="u1", source="indeed", description="Python React"),
        JobListing(title="Dev", company="BlacklistedCorp", location="Delhi", url="u2", source="linkedin", description="Python"),
    ]
    filtered = ranker.filter_by_blacklist(jobs)
    assert len(filtered) == 1
    assert filtered[0].company == "Apple"


def test_job_ranker_skill_filtering():
    """Verify JobRanker keeps only jobs with at least 1 skill overlap."""
    ranker = JobRanker(user_skills=["Python", "Docker"])

    jobs = [
        JobListing(title="Python Dev", company="X", location="L", url="u1", source="s", description="Python and Docker environment"),
        JobListing(title="Java Dev", company="Y", location="L", url="u2", source="s", description="Spring Boot microservices"),
    ]
    filtered = ranker.filter_by_skills(jobs, min_skill_overlap=1)
    assert len(filtered) == 1
    assert filtered[0].company == "X"


def test_resume_matcher_ats_good_resume():
    """High-alignment resume should yield ats_score > 0.40 and match key technical terms."""
    matcher = ResumeMatcher()
    job_desc = "Looking for a Python Developer experienced with React, Docker, and AWS."
    resume = "Summary: Experienced Python Developer. Technical skills: React, Docker, AWS, SQL. Education: BE."
    result = matcher.score(job_desc, resume)

    assert result.ats_score > 0.40
    assert "python" in result.matched_keywords
    assert "docker" in result.matched_keywords
    assert "aws" in result.matched_keywords
    # Gaps should not include pure technical terms we covered
    technical_gaps = [g for g in result.gaps if g in ("python", "react", "docker", "aws")]
    assert len(technical_gaps) == 0


def test_resume_matcher_ats_poor_resume():
    """Poor-alignment resume should yield low ats_score and include technical gaps."""
    matcher = ResumeMatcher()
    job_desc = "Looking for a Python Developer experienced with React, Docker, and AWS."
    resume = "Summary: Java Engineer. Experience: Developed Spring Boot microservices with Kubernetes."
    result = matcher.score(job_desc, resume)

    assert result.ats_score < 0.40
    assert "python" in result.gaps


def test_resume_engine_master_loading(tmp_resume_dir):
    """Verify ResumeEngine persists and restores master resume."""
    engine = ResumeEngine(llm_manager=None)
    master = "Name: Md Sadique Amin\nSkills: Java, Python, SQL"
    engine.load_master(master)

    assert engine.get_master() == master
    assert len(engine.get_version_history()) == 1


def test_resume_engine_cover_letter(tmp_resume_dir):
    """Verify template cover letter is generated without LLM."""
    engine = ResumeEngine(llm_manager=None)
    engine.load_master("Name: Test User\nSkills: Python, Docker")

    job = JobListing(
        title="Python Developer", company="Apple",
        location="Bangalore", url="url", source="linkedin",
    )
    cl = engine.generate_cover_letter(job)
    assert "Apple" in cl
    assert "Python Developer" in cl
