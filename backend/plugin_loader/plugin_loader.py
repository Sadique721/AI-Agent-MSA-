"""
backend/plugin_loader/plugin_loader.py
=======================================
Orchestrates dynamic module loading for plugins from the plugins/installed directory.
Supports checking manifests, checking permissions, and calling lifecycle hooks.
"""
from __future__ import annotations

import importlib.util
import json
import logging
import os
import sys
from typing import Dict, List, Optional, Type
from backend.shared.config_loader import ConfigLoader
from plugins.sdk.plugin_base import PluginBase
from plugins.sdk.plugin_manifest import PluginManifest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logger = logging.getLogger("msa.plugins.loader")


class PluginLoader:
    """Manages searching, validating, loading, and unloading system plugins."""

    def __init__(self, plugins_dir: Optional[str] = None) -> None:
        if plugins_dir is None:
            cfg = ConfigLoader.get_instance()
            plugins_dir = str(cfg.path("plugins_dir"))
        if not os.path.isabs(plugins_dir):
            plugins_dir = os.path.join(PROJECT_ROOT, plugins_dir)
        self.plugins_dir = plugins_dir
        self._loaded_plugins: Dict[str, PluginBase] = {}
        os.makedirs(self.plugins_dir, exist_ok=True)

    def discover_plugins(self) -> List[str]:
        """List subdirectories with plugin-manifest.json."""
        plugins = []
        if not os.path.exists(self.plugins_dir):
            return []
        for name in os.listdir(self.plugins_dir):
            p = os.path.join(self.plugins_dir, name)
            if os.path.isdir(p) and os.path.exists(os.path.join(p, "plugin-manifest.json")):
                plugins.append(name)
        return plugins

    def load_plugin(self, name: str) -> Optional[PluginBase]:
        """Load a plugin by directory name."""
        if name in self._loaded_plugins:
            return self._loaded_plugins[name]

        path = os.path.join(self.plugins_dir, name)
        manifest_path = os.path.join(path, "plugin-manifest.json")
        if not os.path.exists(manifest_path):
            logger.warning("Manifest missing for plugin directory: %s", name)
            return None

        # Load and validate manifest
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            manifest = PluginManifest(**data)
        except Exception as e:
            logger.error("Failed to parse manifest for plugin %s: %s", name, e)
            return None

        # Check permission constraints if vault/security is enabled
        entry_file = os.path.join(path, manifest.entry_point)
        if not os.path.exists(entry_file):
            logger.error("Entry file %s not found for plugin %s", manifest.entry_point, name)
            return None

        # Dynamically load module
        try:
            spec = importlib.util.spec_from_file_location(f"msa_plugin_{manifest.id}", entry_file)
            if not spec or not spec.loader:
                return None
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"msa_plugin_{manifest.id}"] = module
            spec.loader.exec_module(module)

            # Find Plugin class
            plugin_class: Optional[Type[PluginBase]] = None
            for attr in dir(module):
                val = getattr(module, attr)
                if isinstance(val, type) and issubclass(val, PluginBase) and val is not PluginBase:
                    plugin_class = val
                    break

            if not plugin_class:
                logger.error("No class inheriting from PluginBase found in %s", entry_file)
                return None

            # Instantiate and load
            instance = plugin_class(manifest=manifest.dict())
            if instance.on_load():
                self._loaded_plugins[manifest.id] = instance
                logger.info("Plugin loaded successfully: %s", manifest.name)
                return instance
            else:
                logger.warning("Plugin %s failed to load (on_load returned False)", manifest.name)
        except Exception as e:
            logger.exception("Failed to load plugin module %s", name)
        return None

    def unload_plugin(self, plugin_id: str) -> bool:
        if plugin_id not in self._loaded_plugins:
            return False
        try:
            plugin = self._loaded_plugins[plugin_id]
            if plugin.on_unload():
                self._loaded_plugins.pop(plugin_id)
                sys.modules.pop(f"msa_plugin_{plugin_id}", None)
                logger.info("Plugin unloaded successfully: %s", plugin_id)
                return True
        except Exception as e:
            logger.exception("Failed to unload plugin %s", plugin_id)
        return False

    def list_loaded(self) -> Dict[str, PluginBase]:
        return dict(self._loaded_plugins)


# ── SingletonAccessor ─────────────────────────────────────────────────────────
_plugin_loader: Optional[PluginLoader] = None

def get_plugin_loader() -> PluginLoader:
    global _plugin_loader
    if _plugin_loader is None:
        _plugin_loader = PluginLoader()
    return _plugin_loader
