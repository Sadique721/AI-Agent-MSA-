"""
plugins/sdk/plugin_manifest.py
===============================
Pydantic schemas and schema validation helper for plugin manifests.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator


class PluginManifest(BaseModel):
    """Configuration structure for plugin-manifest.json."""
    id: str = Field(..., description="Unique slugified ID of the plugin (e.g. system-monitor)")
    name: str = Field(..., description="Human-readable name")
    version: str = Field(default="1.0.0", description="Semver version string")
    description: str = Field(default="", description="Summary of what the plugin does")
    author: str = Field(default="unknown", description="Author details")
    entry_point: str = Field(default="plugin.py", description="Main python file containing Plugin class")
    permissions: List[str] = Field(default_factory=list, description="Requested tool/filesystem permissions")
    dependencies: List[str] = Field(default_factory=list, description="Plugin dependencies")

    @validator("id")
    def validate_slug(cls, v):
        import re
        if not re.match(r"^[a-z0-9_\-]+$", v):
            raise ValueError("Plugin ID must be a lowercase slug containing only alphanumeric, underscore, or hyphen characters.")
        return v
