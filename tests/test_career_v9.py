"""
tests/test_career_v9.py
=======================
Unit tests for Phase 4 (V9 CRM, Analytics, and Outreach) modules.

All tests use separate tmp_path-isolated databases via monkeypatch
to avoid Windows WinError 32 PermissionErrors from shared connections.
"""
import os
import pytest
from datetime import datetime, timezone
from career.job_models import RecruiterContact


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture()
def crm(tmp_path, monkeypatch):
    """Isolated RecruiterCRM with a fresh per-test SQLite db."""
    import config
    monkeypatch.setattr(config, "RECRUITER_CRM_DB", str(tmp_path / "crm.db"))
    # Re-import so the module picks up the patched config value
    import importlib
    import career.recruiter_crm as mod
    importlib.reload(mod)
    return mod.RecruiterCRM()


@pytest.fixture()
def tracker(tmp_path, monkeypatch):
    """Isolated InterviewTracker with a fresh per-test SQLite db."""
    import config
    db = str(tmp_path / "apps.db")
    monkeypatch.setattr(config, "APPLICATIONS_DB", db)
    import importlib
    import career.interview_tracker as mod
    importlib.reload(mod)
    t = mod.InterviewTracker()
    # Seed applications table so FK constraint is satisfied
    t._db.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            job_id TEXT PRIMARY KEY, status TEXT, applied_at TEXT,
            cover_letter_version TEXT, resume_version TEXT, screenshots TEXT,
            notes TEXT, follow_up_date TEXT, rejection_reason TEXT, interview_date TEXT
        )
    """)
    t._db.execute("INSERT INTO applications (job_id, status) VALUES ('job_999', 'discovered')")
    t._db.commit()
    return t


@pytest.fixture()
def analytics(tmp_path, monkeypatch):
    """Isolated CareerAnalytics with a fresh per-test SQLite db."""
    import config
    db = str(tmp_path / "apps.db")
    monkeypatch.setattr(config, "APPLICATIONS_DB", db)
    monkeypatch.setattr(config, "ANALYTICS_REPORT_DIR", str(tmp_path / "reports"))
    import importlib
    import career.analytics as mod
    importlib.reload(mod)
    instance = mod.CareerAnalytics()
    # Pre-create table so tests don't need to create it manually
    instance._db.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            job_id TEXT PRIMARY KEY, status TEXT, applied_at TEXT,
            cover_letter_version TEXT, resume_version TEXT, screenshots TEXT,
            notes TEXT, follow_up_date TEXT, rejection_reason TEXT, interview_date TEXT
        )
    """)
    instance._db.commit()
    return instance


# ─── RecruiterCRM tests ───────────────────────────────────────────────────────

def test_crm_add_and_get_contact(crm):
    """Verify contact addition and retrieval by id."""
    contact = RecruiterContact(name="Alice Smith", company="Netflix", email="alice@netflix.com")
    crm.add_contact(contact)

    loaded = crm.get_contact(contact.id)
    assert loaded is not None
    assert loaded.name == "Alice Smith"
    assert loaded.company == "Netflix"


def test_crm_list_contacts(crm):
    """Each fixture gets a fresh DB — count should be exactly 2."""
    crm.add_contact(RecruiterContact(name="Bob", company="X"))
    crm.add_contact(RecruiterContact(name="Carol", company="Y"))

    contacts = crm.list_contacts()
    assert len(contacts) == 2
    names = {c.name for c in contacts}
    assert "Bob" in names
    assert "Carol" in names


def test_crm_outreach_logging(crm):
    """Outreach logging updates last_contacted timestamp."""
    contact = RecruiterContact(name="Dave", company="Amazon")
    crm.add_contact(contact)
    crm.log_outreach(contact.id, "email", "Hi Dave!")

    loaded = crm.get_contact(contact.id)
    assert loaded.last_contacted is not None


def test_crm_followup_scheduling_and_pending(crm):
    """Follow-ups scheduled in the past appear in pending list."""
    contact = RecruiterContact(name="Eve", company="Meta")
    crm.add_contact(contact)
    crm.schedule_followup(contact.id, "2020-01-01", "Follow-up template")

    pending = crm.get_pending_followups()
    assert len(pending) == 1
    assert pending[0]["name"] == "Eve"


def test_crm_mark_followup_completed(crm):
    """Completed follow-ups disappear from the pending list."""
    contact = RecruiterContact(name="Frank", company="Tesla")
    crm.add_contact(contact)
    crm.schedule_followup(contact.id, "2020-01-01")

    # Mark as done
    crm.mark_followup_completed(contact.id)

    # Query uses today's date; 2020-01-01 <= today → still matched BUT completed=1
    pending = crm.get_pending_followups()
    assert len(pending) == 0


# ─── InterviewTracker tests ───────────────────────────────────────────────────

def test_interview_round_logging(tracker):
    """InterviewTracker records a coding round correctly."""
    tracker.log_round("job_999", "coding_round", "2026-08-01T10:00:00", "John Doe", "Algorithms")

    rounds = tracker.get_rounds("job_999")
    assert len(rounds) == 1
    assert rounds[0]["round_name"] == "coding_round"
    assert rounds[0]["interviewer"] == "John Doe"


def test_interview_feedback_update(tracker):
    """Feedback update sets result and feedback fields on a round."""
    tracker.log_round("job_999", "system_design", "2026-08-05T14:00:00")
    rounds = tracker.get_rounds("job_999")
    tracker.log_feedback(rounds[0]["id"], "pass", "Excellent design")

    updated = tracker.get_rounds("job_999")
    assert updated[0]["result"] == "pass"
    assert updated[0]["feedback"] == "Excellent design"


# ─── CareerAnalytics tests ────────────────────────────────────────────────────

def test_analytics_funnel_aggregation(analytics):
    """Funnel stats correctly count applications per status."""
    analytics._db.execute("INSERT INTO applications (job_id, status) VALUES ('j1', 'applied')")
    analytics._db.execute("INSERT INTO applications (job_id, status) VALUES ('j2', 'interview')")
    analytics._db.execute("INSERT INTO applications (job_id, status) VALUES ('j3', 'rejected')")
    analytics._db.commit()

    funnel = analytics.get_funnel_stats()
    assert funnel["applied"] == 1
    assert funnel["interview"] == 1
    assert funnel["rejected"] == 1


def test_analytics_response_rates(analytics):
    """Response rate = (interview + rejected) / total_applied."""
    # Each test gets a fresh DB; no UNIQUE violation risk
    analytics._db.execute("INSERT INTO applications (job_id, status) VALUES ('r1', 'applied')")
    analytics._db.execute("INSERT INTO applications (job_id, status) VALUES ('r2', 'interview')")
    analytics._db.execute("INSERT INTO applications (job_id, status) VALUES ('r3', 'rejected')")
    analytics._db.commit()

    rates = analytics.get_response_rates()
    assert rates["total_applied"] == 3
    # response = interview + rejected = 2; rate = 2/3 ≈ 0.6667
    assert abs(rates["response_rate"] - round(2 / 3, 4)) < 0.001
