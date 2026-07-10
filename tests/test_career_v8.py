"""
tests/test_career_v8.py
=======================
Unit tests for Phase 3 (V8 Autonomous Application Engine) modules:
  - RecoveryEngine checkpoint save / restore / clear cycle
  - ApplicationEngine staged lifecycle (queued mode, SQLite persistence)

Uses tmp_path to isolate each test's SQLite files from open connections.
"""
import os
import pytest
from career.job_models import JobListing
from career.recovery_engine import RecoveryEngine


@pytest.fixture()
def isolated_apps_db(tmp_path, monkeypatch):
    """
    Patches APPLICATIONS_DB and EVIDENCE_DIR to a temporary directory so that
    no test shares an open SQLite connection with another test.
    """
    import config
    db_path = str(tmp_path / "applications.db")
    evidence_dir = str(tmp_path / "evidence")
    monkeypatch.setattr(config, "APPLICATIONS_DB", db_path)
    monkeypatch.setattr(config, "EVIDENCE_DIR", evidence_dir)
    os.makedirs(evidence_dir, exist_ok=True)
    return db_path


@pytest.fixture()
def isolated_checkpoint_dir(tmp_path, monkeypatch):
    """Patches _CHECKPOINT_DIR inside recovery_engine to tmp_path."""
    import career.recovery_engine as rmod
    monkeypatch.setattr(rmod, "_CHECKPOINT_DIR", str(tmp_path / "checkpoints"))
    os.makedirs(str(tmp_path / "checkpoints"), exist_ok=True)


def test_recovery_engine_checkpoint_save_restore(isolated_checkpoint_dir):
    """RecoveryEngine saves checkpoint and restores exact state."""
    recovery = RecoveryEngine()
    job_id = "test_job_123"
    state = {"stage": "skills_form", "input_index": 4}

    recovery.checkpoint(job_id, "step_2", state)
    restored = recovery.restore(job_id)

    assert restored is not None
    assert restored["step"] == "step_2"
    assert restored["state"]["stage"] == "skills_form"
    assert restored["state"]["input_index"] == 4


def test_recovery_engine_clear(isolated_checkpoint_dir):
    """RecoveryEngine clears checkpoint so restore returns None."""
    recovery = RecoveryEngine()
    job_id = "test_clear_job"

    recovery.checkpoint(job_id, "filling_form", {"page": 1})
    assert recovery.restore(job_id) is not None

    recovery.clear(job_id)
    assert recovery.restore(job_id) is None


def test_recovery_engine_no_checkpoint(isolated_checkpoint_dir):
    """restore() returns None when no checkpoint file exists."""
    recovery = RecoveryEngine()
    assert recovery.restore("nonexistent_job_xyz") is None


def test_application_engine_staged_queued(isolated_apps_db):
    """ApplicationEngine stages application as 'queued' when AUTO_APPLY is False."""
    # Re-import after monkeypatch to get fresh DB path
    import importlib
    import career.application_engine as ae_mod
    importlib.reload(ae_mod)
    ApplicationEngine = ae_mod.ApplicationEngine

    engine = ApplicationEngine()
    job = JobListing(
        title="Frontend Dev",
        company="Microsoft",
        location="Hyderabad",
        url="https://careers.microsoft.com/jobs/456",
        source="company",
    )

    # AUTO_APPLY_ENABLED is False by default — should stage as queued
    record = engine.apply(job, force=False)
    assert record.status == "queued"
    assert "Awaiting user confirmation" in record.notes

    # Confirm it's persisted in SQLite
    loaded = engine._load_record(job.id)
    assert loaded is not None
    assert loaded.status == "queued"
    assert loaded.job_id == job.id
