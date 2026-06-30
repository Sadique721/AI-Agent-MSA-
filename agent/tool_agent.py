"""
agent/tool_agent.py
====================
MCP-compatible Tool Execution Agent for MSA AI Agent V5.0.
Executes tools with per-tool permission checks and sandboxed subprocess support.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger("msa.agent.tool")

# ── Tool Result ───────────────────────────────────────────────────────────────
class ToolResult:
    def __init__(self, tool: str, success: bool, output: str, error: str = "", duration_ms: float = 0.0):
        self.tool = tool
        self.success = success
        self.output = output
        self.error = error
        self.duration_ms = duration_ms

    def to_dict(self) -> Dict:
        return {
            "tool": self.tool,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
        }

    def __str__(self) -> str:
        return self.output if self.success else f"[ERROR] {self.error}"


# ── Permission Guard ──────────────────────────────────────────────────────────
class PermissionGuard:
    """Validates tool calls against security config."""

    BLOCKED_SHELL_PATTERNS = [
        "rm -rf /", "format c:", "del /f /q /s c:\\",
        "shutdown", ":(){ :|:& };:", "> /dev/sda",
        "dd if=/dev/zero", "mkfs", "fdisk",
    ]

    def __init__(self, security_config: Optional[Dict] = None) -> None:
        self._cfg = security_config or {}

    def check(self, tool_name: str, params: Dict) -> tuple[bool, str]:
        """Returns (allowed: bool, reason: str)."""
        tool_cfg = self._cfg.get("tool_permissions", {}).get(tool_name, {})
        if not tool_cfg.get("enabled", True):
            return False, f"Tool '{tool_name}' is disabled in security config"

        if tool_name == "filesystem":
            path_str = str(params.get("path", ""))
            denied = tool_cfg.get("denied_paths", [])
            for denied_path in denied:
                if path_str.lower().startswith(denied_path.lower()):
                    return False, f"Path '{path_str}' is in the denied list"
            if not tool_cfg.get("write_allowed", True) and params.get("mode") == "write":
                return False, "Filesystem write is disabled"

        if tool_name == "terminal":
            command = str(params.get("command", "")).lower()
            blacklist = tool_cfg.get("command_blacklist", []) + self.BLOCKED_SHELL_PATTERNS
            for blocked in blacklist:
                if blocked.lower() in command:
                    return False, f"Command contains blocked pattern: '{blocked}'"

        return True, "allowed"


# ── Built-in Tool Implementations ────────────────────────────────────────────
class ToolRegistry:
    """Registry of built-in tools with MCP-compatible interface."""

    def __init__(self, guard: PermissionGuard) -> None:
        self._guard = guard
        self._tools: Dict[str, Callable] = {
            "filesystem_read": self._filesystem_read,
            "filesystem_write": self._filesystem_write,
            "filesystem_list": self._filesystem_list,
            "terminal": self._terminal,
            "web_search": self._web_search,
            "git_status": self._git_status,
            "git_diff": self._git_diff,
            "get_system_info": self._system_info,
            "gui_automation": self._gui_automation,
        }

    def available_tools(self) -> List[str]:
        return list(self._tools.keys())

    def execute(self, tool_name: str, params: Dict) -> ToolResult:
        start = time.time()
        allowed, reason = self._guard.check(tool_name, params)
        if not allowed:
            return ToolResult(tool_name, False, "", f"Permission denied: {reason}",
                              (time.time() - start) * 1000)
        fn = self._tools.get(tool_name)
        if not fn:
            return ToolResult(tool_name, False, "", f"Unknown tool: {tool_name}",
                              (time.time() - start) * 1000)
        try:
            output = fn(params)
            return ToolResult(tool_name, True, str(output), "", (time.time() - start) * 1000)
        except Exception as e:
            logger.exception("Tool '%s' raised exception", tool_name)
            return ToolResult(tool_name, False, "", str(e), (time.time() - start) * 1000)

    # ── Tool implementations ──────────────────────────────────────────────────
    def _filesystem_read(self, params: Dict) -> str:
        path = params.get("path", "")
        if not os.path.isabs(path):
            path = os.path.join(PROJECT_ROOT, path)
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        max_chars = params.get("max_chars", 50000)
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n[TRUNCATED: {len(content) - max_chars} chars omitted]"
        return content

    def _filesystem_write(self, params: Dict) -> str:
        path = params.get("path", "")
        content = params.get("content", "")
        if not os.path.isabs(path):
            path = os.path.join(PROJECT_ROOT, path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Written {len(content)} chars to {path}"

    def _filesystem_list(self, params: Dict) -> str:
        path = params.get("path", ".")
        if not os.path.isabs(path):
            path = os.path.join(PROJECT_ROOT, path)
        entries = []
        for item in sorted(Path(path).iterdir()):
            kind = "DIR" if item.is_dir() else "FILE"
            size = f" ({item.stat().st_size:,} bytes)" if item.is_file() else ""
            entries.append(f"  [{kind}] {item.name}{size}")
        return "\n".join(entries) if entries else "(empty directory)"

    def _terminal(self, params: Dict) -> str:
        command = params.get("command", "")
        timeout = int(params.get("timeout", 30))
        cwd = params.get("cwd", PROJECT_ROOT)
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=cwd
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            output = f"[Exit {result.returncode}]\n{result.stderr.strip() or output}"
        return output or "(no output)"

    def _web_search(self, params: Dict) -> str:
        query = params.get("query", "")
        try:
            import urllib.request, urllib.parse
            encoded = urllib.parse.quote(query)
            url = f"https://ddg-api.fly.dev/search?q={encoded}&max_results=5"
            req = urllib.request.Request(url, headers={"User-Agent": "MSA-AI-Agent/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            results = data if isinstance(data, list) else data.get("results", [])
            lines = []
            for r in results[:5]:
                title = r.get("title", "")
                snippet = r.get("body", r.get("snippet", ""))[:300]
                url_r = r.get("href", r.get("url", ""))
                lines.append(f"**{title}**\n{snippet}\n{url_r}")
            return "\n\n".join(lines) if lines else "No results found."
        except Exception as e:
            logger.warning("Web search failed: %s", e)
            return f"Web search unavailable: {e}"

    def _git_status(self, params: Dict) -> str:
        cwd = params.get("cwd", PROJECT_ROOT)
        result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=cwd)
        return result.stdout.strip() or "Working tree clean"

    def _git_diff(self, params: Dict) -> str:
        cwd = params.get("cwd", PROJECT_ROOT)
        file_path = params.get("file", "")
        args = ["git", "diff"]
        if file_path:
            args.append(file_path)
        result = subprocess.run(args, capture_output=True, text=True, cwd=cwd)
        output = result.stdout.strip()
        return output[:5000] if output else "No changes"

    def _system_info(self, _: Dict) -> str:
        try:
            import platform, psutil  # type: ignore
            return json.dumps({
                "os": platform.system(),
                "python": platform.python_version(),
                "cpu_percent": psutil.cpu_percent(interval=0.5),
                "memory_percent": psutil.virtual_memory().percent,
            }, indent=2)
        except ImportError:
            import platform
            return json.dumps({"os": platform.system(), "python": platform.python_version()})

    def _gui_automation(self, params: Dict) -> str:
        action = params.get("action", "")
        from agent.tools.gui_automation import execute_gui_action
        res = execute_gui_action(action, params)
        return json.dumps(res)


# ── Tool Agent ────────────────────────────────────────────────────────────────
class ToolAgent:
    """
    Selects and executes the appropriate tool based on planner output.
    Supports sequential and parallel (future) tool execution.
    """

    def __init__(self, security_config: Optional[Dict] = None) -> None:
        self._guard = PermissionGuard(security_config)
        self._registry = ToolRegistry(self._guard)

    def execute_tool(self, tool_name: str, params: Dict) -> ToolResult:
        logger.info("Executing tool: %s | params: %s", tool_name, list(params.keys()))
        if tool_name in self._registry.available_tools():
            return self._registry.execute(tool_name, params)

        # Fallback to registered MCP servers
        try:
            from backend.mcp.mcp_registry import get_mcp_registry
            from backend.mcp.mcp_client import MCPClient
            registry = get_mcp_registry()
            for sinfo in registry.list_servers():
                if tool_name.startswith(sinfo["name"]):
                    client = MCPClient(sinfo["name"], sinfo["command"], sinfo["args"], sinfo["env"])
                    if not client.start():
                        return ToolResult(tool_name, False, "", f"Failed to start MCP server {sinfo['name']}", 0.0)
                    try:
                        t0 = time.time()
                        output = client.call_tool(tool_name, params)
                        duration = (time.time() - t0) * 1000
                        client.stop()
                        return ToolResult(tool_name, True, json.dumps(output), "", duration)
                    except Exception as ex:
                        client.stop()
                        return ToolResult(tool_name, False, "", str(ex), 0.0)
        except Exception as e:
            logger.error("Failed executing MCP fallback: %s", e)

        return ToolResult(tool_name, False, "", f"Unknown tool: {tool_name}", 0.0)

    def execute_steps(self, steps: List[Dict]) -> List[Dict]:
        """Execute a list of planner steps and return results."""
        results = []
        for step in steps:
            action = step.get("action", "")
            tool = step.get("tool")
            params = step.get("params", {})
            if action == "tool_call" and tool:
                result = self.execute_tool(tool, params)
                results.append(result.to_dict())
            else:
                results.append({"step": step.get("id"), "skipped": True, "reason": "not a tool_call"})
        return results

    def available_tools(self) -> List[str]:
        return self._registry.available_tools()


# ── Module-level singleton ────────────────────────────────────────────────────
_tool_agent: Optional[ToolAgent] = None


def get_tool_agent(security_config: Optional[Dict] = None) -> ToolAgent:
    global _tool_agent
    if _tool_agent is None:
        _tool_agent = ToolAgent(security_config)
    return _tool_agent
