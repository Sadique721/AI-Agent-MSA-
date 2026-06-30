import logging
from typing import Dict, Any, List

logger = logging.getLogger("msa.mcp.registry")

class MCPRegistry:
    def __init__(self):
        self.servers: Dict[str, Dict[str, Any]] = {}
        self.load_defaults()

    def load_defaults(self):
        # Default registered local/remote MCP server definitions
        self.servers["sqlite-mcp"] = {
            "name": "sqlite-mcp",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sqlite"],
            "env": {},
            "status": "registered"
        }
        self.servers["filesystem-mcp"] = {
            "name": "filesystem-mcp",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"],
            "env": {},
            "status": "registered"
        }

    def register_server(self, name: str, command: str, args: List[str], env: Dict[str, str] = None) -> None:
        self.servers[name] = {
            "name": name,
            "command": command,
            "args": args,
            "env": env or {},
            "status": "registered"
        }
        logger.info(f"Registered MCP server: {name}")

    def get_server(self, name: str) -> Dict[str, Any]:
        return self.servers.get(name)

    def list_servers(self) -> List[Dict[str, Any]]:
        return list(self.servers.values())

_registry_instance = None

def get_mcp_registry() -> MCPRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = MCPRegistry()
    return _registry_instance
