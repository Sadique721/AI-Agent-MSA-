"""
backend/artifact_engine/artifact_service.py
=============================================
Orchestrates creating, updating, versioning, and rendering artifacts.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional
from backend.artifact_engine.artifact_models import Artifact, ArtifactVersion
from backend.artifact_engine.artifact_store import ArtifactStore

logger = logging.getLogger("msa.artifacts")


class ArtifactService:
    """Business logic coordinator for version-tracked Claude-style artifacts."""

    def __init__(self, store: Optional[ArtifactStore] = None) -> None:
        self._store = store or ArtifactStore()

    def create_artifact(
        self,
        title: str,
        file_type: str,
        content: str,
        language: Optional[str] = None,
        workspace_id: str = "default",
    ) -> Artifact:
        """Create a new artifact with version 1."""
        slug = title.lower().replace(" ", "_").replace("-", "_")
        
        # Ensure slug is unique
        existing = self._store.get_artifact(slug)
        counter = 1
        original_slug = slug
        while existing:
            slug = f"{original_slug}_{counter}"
            existing = self._store.get_artifact(slug)
            counter += 1

        now = time.time()
        art = Artifact(
            id=slug,
            title=title,
            file_type=file_type,
            language=language,
            workspace_id=workspace_id,
            current_version=1,
            created_at=now,
            updated_at=now,
        )
        self._store.save_artifact(art, new_content=content, change_desc="Initial creation")
        logger.info("Created artifact: %s (slug: %s)", title, slug)
        return self._store.get_artifact(slug) or art

    def update_artifact(self, artifact_id: str, new_content: str, change_desc: str = "") -> Optional[Artifact]:
        """Create a new version increments of the artifact."""
        art = self._store.get_artifact(artifact_id)
        if not art:
            logger.warning("Attempted to update non-existent artifact: %s", artifact_id)
            return None

        art.current_version += 1
        art.updated_at = time.time()
        self._store.save_artifact(art, new_content=new_content, change_desc=change_desc)
        logger.info("Updated artifact %s to version %d", artifact_id, art.current_version)
        return self._store.get_artifact(artifact_id)

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        return self._store.get_artifact(artifact_id)

    def list_workspace_artifacts(self, workspace_id: str) -> List[Artifact]:
        return self._store.list_artifacts(workspace_id)

    def delete_artifact(self, artifact_id: str) -> bool:
        return self._store.delete_artifact(artifact_id)


# ── SingletonAccessor ─────────────────────────────────────────────────────────
_artifact_service: Optional[ArtifactService] = None

def get_artifact_service() -> ArtifactService:
    global _artifact_service
    if _artifact_service is None:
        _artifact_service = ArtifactService()
    return _artifact_service
