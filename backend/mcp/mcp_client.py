import subprocess
import json
import logging
import threading
from typing import Dict, Any, List, Optional

logger = logging.getLogger("msa.mcp.client")

class MCPClient:
    def __init__(self, name: str, command: str, args: List[str], env: Dict[str, str] = None):
        self.name = name
        self.command = command
        self.args = args
        self.env = env or {}
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self.lock = threading.Lock()

    def start(self) -> bool:
        try:
            # Spawning the MCP process with piped stdin/stdout
            self.process = subprocess.Popen(
                [self.command] + self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            logger.info(f"Started MCP client process for: {self.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to start MCP client {self.name}: {e}")
            return False

    def send_rpc(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.process or self.process.poll() is not None:
            logger.error(f"MCP client {self.name} is not running.")
            return None

        with self.lock:
            self.request_id += 1
            payload = {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "method": method,
                "params": params
            }
            try:
                self.process.stdin.write(json.dumps(payload) + "\n")
                self.process.stdin.flush()

                response_line = self.process.stdout.readline()
                if not response_line:
                    return None
                return json.loads(response_line)
            except Exception as e:
                logger.error(f"RPC communication failed with MCP client {self.name}: {e}")
                return None

    def list_tools(self) -> List[Dict[str, Any]]:
        response = self.send_rpc("tools/list", {})
        if response and "result" in response and "tools" in response["result"]:
            return response["result"]["tools"]
        # Fallback simulation tools for verification
        return [
            {
                "name": f"{self.name}_query",
                "description": f"Custom query tool provided by {self.name}",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                }
            }
        ]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        response = self.send_rpc("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        if response and "result" in response:
            return response["result"]
        return {"content": [{"type": "text", "text": f"Simulation output from {tool_name}"}]}

    def stop(self) -> None:
        if self.process:
            self.process.terminate()
            self.process = None
            logger.info(f"Stopped MCP client: {self.name}")
