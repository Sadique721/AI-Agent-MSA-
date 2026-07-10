"""
backend/mcp/tool_hooks.py
==========================
Registers local system tool hooks (filesystem, disk info) into the
EXISTING mcp_registry.py — does not create a second, disconnected MCP
system. Import and call `register_local_hooks(existing_registry)` once
at startup, passing the MCPRegistry instance already created elsewhere.
"""
import os
import shutil
import logging
from typing import Dict, Any

logger = logging.getLogger("msa.mcp.tool_hooks")


def register_local_hooks(registry) -> None:
    """
    `registry` is the existing instance from backend/mcp/mcp_registry.py.
    This function assumes that module exposes a `.register(name, callback)`
    method — adjust the method name below if the existing registry's API
    differs (check backend/mcp/mcp_registry.py's public methods first).
    """
    def _list_dir(args: Dict[str, Any]):
        path = args.get("path", ".")
        return os.listdir(path)

    def _disk_usage(args: Dict[str, Any]):
        path = args.get("path", "/")
        usage = shutil.disk_usage(path)
        return {"total": usage.total, "used": usage.used, "free": usage.free}

    if hasattr(registry, "register_server"):
        # The existing registry has a `.register_server` but let's check if it has a way to register direct hooks/functions.
        # Let's inspect registry. Class MCPRegistry in mcp_registry.py has:
        # def register_server(self, name, command, args, env=None)
        # It holds an internal `self.servers` dict.
        # Since we want it to be compatible, let's see how our new tools are called.
        # MCPClient has `call_tool(tool_name, arguments)`.
        # To avoid breaking existing code, we can define registry.register(name, callback) on the fly, 
        # or store callbacks on the registry object itself. Let's add the register method dynamically or support it here.
        pass

    # We add register method to the registry dynamically if it doesn't exist so we can store hook callbacks
    if not hasattr(registry, "local_hooks"):
        registry.local_hooks = {}
        
    def custom_register(name: str, callback) -> None:
        registry.local_hooks[name] = callback
        logger.info("Registered local hook: %s", name)
        
    registry.register = custom_register
    registry.register("fs_list_dir", _list_dir)
    registry.register("fs_disk_usage", _disk_usage)
    logger.info("MCP local tool hooks registered into existing registry.")
