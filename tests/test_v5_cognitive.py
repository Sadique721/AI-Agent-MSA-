import os
import pytest
from backend.shared.operating_mode import get_operating_mode_manager, OperatingMode
from backend.backup.backup_service import get_backup_service
from backend.auto_update.update_service import get_update_service
from backend.services.background_agent_coordinator import get_background_coordinator
from typing import List

def test_operating_modes():
    mgr = get_operating_mode_manager()
    mgr.set_mode(OperatingMode.SAFE)
    assert mgr.get_mode() == OperatingMode.SAFE
    assert mgr.is_terminal_allowed() is False
    assert "web_search" not in mgr.get_allowed_tools()

    mgr.set_mode(OperatingMode.OFFLINE)
    assert mgr.is_internet_allowed() is False
    assert "terminal" in mgr.get_allowed_tools()

    mgr.set_mode(OperatingMode.HYBRID)
    assert mgr.is_internet_allowed() is True
    assert mgr.is_terminal_allowed() is True

def test_backup_restore():
    service = get_backup_service()
    
    # Create backup
    zip_path = service.create_backup()
    assert os.path.exists(zip_path) is True
    filename = os.path.basename(zip_path)

    # List backups
    backups = service.list_backups()
    assert filename in backups

    # Restore backup
    assert service.restore_backup(filename) is True

    # Clean up zip
    os.remove(zip_path)

def test_auto_update():
    service = get_update_service()
    info = service.check_for_updates()
    assert "current_version" in info
    assert "latest_version" in info
    assert info["has_update"] is True

    # Apply update simulation
    assert service.apply_update() is True
    assert service.current_version == "5.0.1"

def test_background_coordinator():
    coord = get_background_coordinator()
    coord.start()
    assert coord._running is True
    coord.stop()
    assert coord._running is False
