"""
backend/workspace_manager/workspace_service.py
================================================
Workspace Service coordinator.
Manages workspace CRUD, active workspace switching, and isolated namespaces.
"""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional
from backend.workspace_manager.workspace_models import Workspace, WorkspaceConfig
from backend.workspace_manager.workspace_store import WorkspaceStore

logger = logging.getLogger("msa.workspaces")


class WorkspaceService:
    """Core service orchestrating workspaces and namespaces."""

    def __init__(self, store: Optional[WorkspaceStore] = None) -> None:
        self._store = store or WorkspaceStore()
        self._active_workspace_id = "default"

    def get_active_workspace(self) -> Workspace:
        ws = self._store.get_workspace(self._active_workspace_id)
        if not ws:
            ws = self._store.get_workspace("default")
            # If default is somehow missing, it will auto-create
        return ws or Workspace(id="default", name="Default Workspace")

    def set_active_workspace(self, workspace_id: str) -> bool:
        ws = self._store.get_workspace(workspace_id)
        if ws:
            self._active_workspace_id = workspace_id
            logger.info("Switched to workspace: %s", workspace_id)
            return True
        logger.warning("Attempted to switch to invalid workspace: %s", workspace_id)
        return False

    def create_workspace(self, name: str, description: str = "", root_path: str = ".") -> Workspace:
        slug = name.lower().replace(" ", "_").replace("-", "_")
        # Ensure slug is unique
        existing = self._store.get_workspace(slug)
        counter = 1
        original_slug = slug
        while existing:
            slug = f"{original_slug}_{counter}"
            existing = self._store.get_workspace(slug)
            counter += 1

        import time
        ws = Workspace(
            id=slug,
            name=name,
            description=description,
            root_path=root_path,
            config=WorkspaceConfig(),
            created_at=time.time(),
            updated_at=time.time(),
        )
        self._store.save_workspace(ws)
        logger.info("Created workspace: %s (%s)", name, slug)
        return ws

    def list_workspaces(self) -> List[Workspace]:
        return self._store.list_workspaces()

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        return self._store.get_workspace(workspace_id)

    def update_workspace_config(self, workspace_id: str, config: WorkspaceConfig) -> Optional[Workspace]:
        ws = self._store.get_workspace(workspace_id)
        if not ws:
            return None
        ws.config = config
        ws.updated_at = os.path.getmtime(ws.root_path) if os.path.exists(ws.root_path) else 0.0
        self._store.save_workspace(ws)
        return ws

    def delete_workspace(self, workspace_id: str) -> bool:
        if workspace_id == "default":
            return False
        if self._active_workspace_id == workspace_id:
            self._active_workspace_id = "default"
        return self._store.delete_workspace(workspace_id)


# ── SingletonAccessor ─────────────────────────────────────────────────────────
_workspace_service: Optional[WorkspaceService] = None

def get_workspace_service() -> WorkspaceService:
    global _workspace_service
    if _workspace_service is None:
        _workspace_service = WorkspaceService()
    return _workspace_service
