# Plugin SDK Guide — MSA V5.0

The MSA AI Agent V5.0 contains a lightweight Plugin SDK allowing you to expand the capabilities of the agent by registering custom tools, integrations, and lifecycle watchers.

---

## 1. Directory Structure

Place your custom plugins inside `plugins/installed/`:
```
plugins/installed/
└── system-health-checker/
    ├── plugin-manifest.json
    └── plugin.py
```

---

## 2. Manifest Schema (`plugin-manifest.json`)

The manifest defines the configuration, permissions, and entry point of your plugin:

```json
{
  "id": "system-health-checker",
  "name": "System Health Checker",
  "version": "1.0.0",
  "description": "Monitors cpu temperature and memory exhaustion risk.",
  "author": "Md Sadique Amin",
  "entry_point": "plugin.py",
  "permissions": ["terminal"],
  "dependencies": []
}
```

---

## 3. Creating the Entry Point (`plugin.py`)

All plugins must subclass `PluginBase` from `plugins.sdk.plugin_base` and implement `on_load()` and `on_unload()` hooks:

```python
import logging
from plugins.sdk.plugin_base import PluginBase

logger = logging.getLogger("msa.plugin.health")

class HealthCheckerPlugin(PluginBase):
    
    def on_load(self) -> bool:
        """Executed when the gateway loads the plugin."""
        logger.info("Health Checker loaded! Hooking into telemetry stream...")
        # Setup background timers or register custom tools here
        return True

    def on_unload(self) -> bool:
        """Executed during cleanup or unloading."""
        logger.info("Cleaning up health checker resources...")
        return True
```

---

## 4. Loading the Plugin

The `PluginLoader` discovers and validates plugins automatically during FastAPI application startup. You can also trigger it programmatically:

```python
from backend.plugin_loader.plugin_loader import get_plugin_loader

loader = get_plugin_loader()
plugin = loader.load_plugin("system-health-checker")
```
