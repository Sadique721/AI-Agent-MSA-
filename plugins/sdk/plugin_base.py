"""
plugins/sdk/plugin_base.py
===========================
Base abstract class for all custom plugins in MSA AI Agent V5.0.
Every plugin must inherit from this class and implement on_load and on_unload.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

logger = logging.getLogger("msa.plugins.sdk")


class PluginBase(ABC):
    """Abstract base class establishing plugin lifecycle hooks."""

    def __init__(self, manifest: Dict[str, Any]) -> None:
        self.manifest = manifest
        self.id = manifest.get("id", "")
        self.name = manifest.get("name", "")
        self.version = manifest.get("version", "1.0.0")

    @abstractmethod
    def on_load(self) -> bool:
        """Called when plugin is loaded into the gateway server. Returns True on success."""
        pass

    @abstractmethod
    def on_unload(self) -> bool:
        """Called when unloading/cleaning up resources. Returns True on success."""
        pass

    def get_info(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.manifest.get("description", ""),
        }
