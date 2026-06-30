"""
backend/backup/backup_service.py
=================================
Automated backup and restore manager for MSA V5.0.
Packages database stores, configurations, and templates into timestamped zip archives.
"""
from __future__ import annotations

import logging
import os
import shutil
import time
import zipfile
from typing import List, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logger = logging.getLogger("msa.backup")


class BackupService:
    """Manages backups of data, config, and prompt files."""

    def __init__(self, backup_dir: str = "data/backups") -> None:
        if not os.path.isabs(backup_dir):
            backup_dir = os.path.join(PROJECT_ROOT, backup_dir)
        self.backup_dir = backup_dir
        os.makedirs(self.backup_dir, exist_ok=True)

    def create_backup(self) -> str:
        """
        ZIP databases, configs, and prompts.
        Returns the absolute path to the generated backup ZIP.
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_filename = f"msa_backup_{timestamp}.zip"
        backup_path = os.path.join(self.backup_dir, backup_filename)

        targets = [
            ("data/memory", "memory"),
            ("config", "config"),
            ("prompts", "prompts"),
        ]

        try:
            with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for rel_src, arc_prefix in targets:
                    src_dir = os.path.join(PROJECT_ROOT, rel_src)
                    if os.path.exists(src_dir):
                        for root, _, files in os.walk(src_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                # Generate path inside archive
                                rel_path = os.path.relpath(file_path, src_dir)
                                arcname = os.path.join(arc_prefix, rel_path)
                                zip_file.write(file_path, arcname)
            logger.info("Backup created successfully: %s", backup_path)
            return backup_path
        except Exception as e:
            logger.exception("Failed to create backup")
            raise RuntimeError(f"Backup creation failed: {e}")

    def list_backups(self) -> List[str]:
        """List filenames of all available backup ZIPs."""
        if not os.path.exists(self.backup_dir):
            return []
        return [
            f for f in sorted(os.listdir(self.backup_dir), reverse=True)
            if f.startswith("msa_backup_") and f.endswith(".zip")
        ]

    def restore_backup(self, backup_filename: str) -> bool:
        """
        Restore configuration and databases from a backup file.
        Returns True on success, raises exception on failure.
        """
        backup_path = os.path.join(self.backup_dir, backup_filename)
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        try:
            with zipfile.ZipFile(backup_path, "r") as zip_ref:
                # Extract to project root
                zip_ref.extractall(PROJECT_ROOT)
            logger.info("Restore completed successfully from: %s", backup_path)
            return True
        except Exception as e:
            logger.exception("Restore failed")
            raise RuntimeError(f"Restore failed: {e}")


# ── SingletonAccessor ─────────────────────────────────────────────────────────
_backup_service: Optional[BackupService] = None

def get_backup_service() -> BackupService:
    global _backup_service
    if _backup_service is None:
        _backup_service = BackupService()
    return _backup_service
