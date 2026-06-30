"""
backend/artifact_engine/artifact_store.py
==========================================
SQLite persistent store for versioned artifacts in MSA V5.0.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from typing import Dict, List, Optional
from backend.artifact_engine.artifact_models import Artifact, ArtifactVersion

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ArtifactStore:
    """Manages artifact metadata and version logs in SQLite."""

    def __init__(self, db_path: str = "data/memory/artifacts.db") -> None:
        if not os.path.isabs(db_path):
            db_path = os.path.join(PROJECT_ROOT, db_path)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._lock = threading.Lock()

        # Create tables
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    language TEXT,
                    workspace_id TEXT NOT NULL,
                    current_version INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS artifact_versions (
                    artifact_id TEXT,
                    version INTEGER,
                    content TEXT NOT NULL,
                    description TEXT,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (artifact_id, version)
                )
                """
            )
            conn.commit()
            conn.close()

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get metadata
            cursor.execute(
                "SELECT title, file_type, language, workspace_id, current_version, created_at, updated_at FROM artifacts WHERE id = ?",
                (artifact_id,)
            )
            meta = cursor.fetchone()
            if not meta:
                conn.close()
                return None

            # Get versions
            cursor.execute(
                "SELECT version, content, description, created_at FROM artifact_versions WHERE artifact_id = ? ORDER BY version ASC",
                (artifact_id,)
            )
            version_rows = cursor.fetchall()
            conn.close()

        versions = [
            ArtifactVersion(
                version=row[0],
                content=row[1],
                description=row[2] or "",
                created_at=row[3]
            ) for row in version_rows
        ]

        return Artifact(
            id=artifact_id,
            title=meta[0],
            file_type=meta[1],
            language=meta[2],
            workspace_id=meta[3],
            current_version=meta[4],
            versions=versions,
            created_at=meta[5],
            updated_at=meta[6]
        )

    def save_artifact(self, art: Artifact, new_content: Optional[str] = None, change_desc: str = "") -> None:
        now = time.time()
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Upsert metadata
            cursor.execute(
                """
                INSERT INTO artifacts (id, title, file_type, language, workspace_id, current_version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    file_type=excluded.file_type,
                    language=excluded.language,
                    workspace_id=excluded.workspace_id,
                    current_version=excluded.current_version,
                    updated_at=?
                """,
                (art.id, art.title, art.file_type, art.language, art.workspace_id, art.current_version, art.created_at or now, now, now)
            )

            # Insert version if new content is specified
            if new_content is not None:
                cursor.execute(
                    """
                    INSERT INTO artifact_versions (artifact_id, version, content, description, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(artifact_id, version) DO UPDATE SET
                        content=excluded.content,
                        description=excluded.description
                    """,
                    (art.id, art.current_version, new_content, change_desc, now)
                )

            conn.commit()
            conn.close()

    def list_artifacts(self, workspace_id: str) -> List[Artifact]:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM artifacts WHERE workspace_id = ?", (workspace_id,))
            rows = cursor.fetchall()
            conn.close()
        
        results = []
        for row in rows:
            art = self.get_artifact(row[0])
            if art:
                results.append(art)
        return results

    def delete_artifact(self, artifact_id: str) -> bool:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM artifacts WHERE id = ?", (artifact_id,))
            cursor.execute("DELETE FROM artifact_versions WHERE artifact_id = ?", (artifact_id,))
            changes = conn.total_changes
            conn.commit()
            conn.close()
            return changes > 0
