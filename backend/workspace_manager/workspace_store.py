"""
backend/workspace_manager/workspace_store.py
=============================================
SQLite persistence store for workspaces in MSA AI Agent V5.0.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from typing import Dict, List, Optional
from backend.workspace_manager.workspace_models import Workspace, WorkspaceConfig

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class WorkspaceStore:
    """Manages workspace storage in a thread-safe SQLite database."""

    def __init__(self, db_path: str = "data/memory/workspaces.db") -> None:
        if not os.path.isabs(db_path):
            db_path = os.path.join(PROJECT_ROOT, db_path)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._lock = threading.Lock()

        # Initialise DB tables
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS workspaces (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    root_path TEXT,
                    config_json TEXT,
                    created_at REAL,
                    updated_at REAL
                )
                """
            )
            conn.commit()
            conn.close()

        # Add default workspace if missing
        self._ensure_default()

    def _ensure_default(self) -> None:
        if not self.get_workspace("default"):
            self.save_workspace(Workspace(
                id="default",
                name="Default Workspace",
                description="Main workspace for general queries and actions.",
                root_path=".",
                created_at=time.time(),
                updated_at=time.time(),
            ))

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, description, root_path, config_json, created_at, updated_at FROM workspaces WHERE id = ?", (workspace_id,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            try:
                cfg_data = json.loads(row[4])
                config = WorkspaceConfig(**cfg_data)
            except Exception:
                config = WorkspaceConfig()

            return Workspace(
                id=row[0],
                name=row[1],
                description=row[2],
                root_path=row[3],
                config=config,
                created_at=row[5],
                updated_at=row[6],
            )

    def list_workspaces(self) -> List[Workspace]:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, description, root_path, config_json, created_at, updated_at FROM workspaces")
            rows = cursor.fetchall()
            conn.close()

        workspaces = []
        for row in rows:
            try:
                cfg_data = json.loads(row[4])
                config = WorkspaceConfig(**cfg_data)
            except Exception:
                config = WorkspaceConfig()

            workspaces.append(Workspace(
                id=row[0],
                name=row[1],
                description=row[2],
                root_path=row[3],
                config=config,
                created_at=row[5],
                updated_at=row[6],
            ))
        return workspaces

    def save_workspace(self, ws: Workspace) -> None:
        config_json = ws.config.json() if hasattr(ws.config, 'json') else json.dumps(ws.config.dict())
        now = time.time()
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO workspaces (id, name, description, root_path, config_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description,
                    root_path=excluded.root_path,
                    config_json=excluded.config_json,
                    updated_at=?
                """,
                (ws.id, ws.name, ws.description, ws.root_path, config_json, ws.created_at or now, now, now),
            )
            conn.commit()
            conn.close()

    def delete_workspace(self, workspace_id: str) -> bool:
        if workspace_id == "default":
            return False  # Never delete default workspace
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM workspaces WHERE id = ?", (workspace_id,))
            changes = conn.total_changes
            conn.commit()
            conn.close()
            return changes > 0
