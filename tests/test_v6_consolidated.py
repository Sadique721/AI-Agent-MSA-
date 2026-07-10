"""
tests/test_v6_consolidated.py
=============================
Integration test suite for V6-V10 Production OS (Phase 5).

Uses monkeypatch + tmp_path to isolate all SQLite databases from open
connections. Tests config validator, schema migrator, health monitor,
crash recovery, and build pipeline dry-run.
"""
import os
import pytest


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def isolated_dbs(tmp_path, monkeypatch):
    """Patches all DB and directory paths to tmp_path so each test is isolated."""
    import config
    monkeypatch.setattr(config, "APPLICATIONS_DB",   str(tmp_path / "applications.db"))
    monkeypatch.setattr(config, "RECRUITER_CRM_DB",  str(tmp_path / "crm.db"))
    monkeypatch.setattr(config, "RESUME_DIR",        str(tmp_path / "resumes"))
    monkeypatch.setattr(config, "EVIDENCE_DIR",      str(tmp_path / "evidence"))
    monkeypatch.setattr(config, "ANALYTICS_REPORT_DIR", str(tmp_path / "analytics"))
    monkeypatch.setattr(config, "LOG_DIR",           str(tmp_path / "logs"))
    # Ensure folders exist
    for subdir in ("resumes", "evidence", "analytics", "logs"):
        os.makedirs(str(tmp_path / subdir), exist_ok=True)
    return tmp_path


# ─── Tests ────────────────────────────────────────────────────────────────────

def test_config_validator(isolated_dbs):
    """Config validator runs cleanly without raising exceptions."""
    from scripts.config_validator import ConfigValidator
    validator = ConfigValidator()
    result = validator.validate_all()
    assert isinstance(result, bool)


def test_db_migrator_creates_tables(isolated_dbs):
    """DBMigrator creates both SQLite schema files at the patched paths."""
    import config
    import importlib
    import scripts.db_migrator as mod
    importlib.reload(mod)  # picks up monkeypatched APPLICATIONS_DB / RECRUITER_CRM_DB
    migrator = mod.DBMigrator()
    assert migrator.run_all() is True
    assert os.path.exists(config.APPLICATIONS_DB)
    assert os.path.exists(config.RECRUITER_CRM_DB)


def test_health_monitor_telemetry(isolated_dbs):
    """HealthMonitor returns expected keys for resource profiling."""
    from backend.health_monitor import HealthMonitor
    monitor = HealthMonitor()
    health = monitor.check_health()

    assert health["status"] in ("healthy", "degraded")
    assert "resources" in health
    assert "cpu_percent" in health["resources"]
    assert "ram_percent" in health["resources"]
    assert "oom_risk" in health["resources"]
    assert "services" in health
    assert "sqlite" in health["services"]


def test_crash_recovery_lifecycle(isolated_dbs):
    """CrashRecovery checkpoint: write → detect → clear."""
    import config
    from backend.crash_recovery import CrashRecovery

    # Point crash checkpoint file inside tmp LOG_DIR
    import backend.crash_recovery as cr_mod
    original_path = cr_mod._CRASH_CHECKPOINT_FILE
    cr_mod._CRASH_CHECKPOINT_FILE = str(isolated_dbs / "logs" / "crash_state.json")

    recovery = CrashRecovery()
    assert recovery.check_for_crash() is None

    recovery.write_checkpoint({"active_apply_job_id": "job_1"})
    assert recovery.check_for_crash() is not None

    recovery.clear_checkpoint()
    assert recovery.check_for_crash() is None

    cr_mod._CRASH_CHECKPOINT_FILE = original_path  # restore


def test_build_pipeline_dry_run(isolated_dbs):
    """Build pipeline dry-run completes with all steps skipped."""
    from scripts.build_pipeline import BuildPipeline
    pipeline = BuildPipeline(dry_run=True)
    result = pipeline.run()

    assert result is True
    assert len(pipeline.reports) == 5
    assert all(r[1] == "SKIP" for r in pipeline.reports)
