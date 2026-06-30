"""
backend/workspace_manager/workspace_models.py
==============================================
Pydantic schemas for Workspace configuration and management in MSA V5.0.
"""
from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class WorkspaceConfig(BaseModel):
    """Isolated environment configuration for a workspace."""
    enable_custom_rules: bool = Field(default=False, description="Enable workspace-specific behavior rules")
    custom_rules: List[str] = Field(default_factory=list, description="Rules specific to this project workspace")
    allowed_tools: List[str] = Field(default_factory=lambda: ["filesystem", "browser", "git"], description="Allowed tools in this workspace")
    model_override: Optional[str] = Field(default=None, description="Force a specific model for this workspace")
    environment_variables: Dict[str, str] = Field(default_factory=dict, description="Workspace-specific environment variables")


class Workspace(BaseModel):
    """Model representing a project workspace."""
    id: str = Field(..., description="Unique slugified ID of the workspace")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(default="", description="Detailed description")
    root_path: str = Field(default=".", description="Path to workspace root on the local filesystem")
    config: WorkspaceConfig = Field(default_factory=WorkspaceConfig, description="Workspace settings")
    created_at: float = Field(default_factory=lambda: 0.0, description="Timestamp created")
    updated_at: float = Field(default_factory=lambda: 0.0, description="Timestamp updated")
