"""
tools/tool_registry.py
=======================
Central registry of all MSA Agent capabilities.

Every tool is a named, typed, documented entry that the Planner Agent
can query and select automatically based on task type.

Tool definition schema:
    {
        "name":        str,   # Unique tool identifier
        "description": str,   # What this tool does (used by Planner)
        "category":    str,   # "system" | "browser" | "mobile" | "memory" | "vision"
        "enabled":     bool,  # Can be toggled by config flags
        "handler":     callable | None,  # Actual function to call (injected later)
        "params":      dict,  # Expected param schema {param_name: type_hint}
        "examples":    list,  # Example commands that map to this tool
    }

Usage:
    registry = ToolRegistry()
    registry.list_enabled()           → list of enabled tool names
    registry.get("open_app")          → tool definition dict
    registry.execute("open_app", {"app": "chrome"})  → result string
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("msa.tools.registry")


# ═══════════════════════════════════════════════════════════════════════════════
# Default Tool Definitions
# ═══════════════════════════════════════════════════════════════════════════════

_DEFAULT_TOOLS: List[Dict] = [
    # ── System Tools ──────────────────────────────────────────────────────────
    {
        "name":        "open_app",
        "description": "Open a desktop application by name (Notepad, Chrome, VS Code, etc.)",
        "category":    "system",
        "enabled":     True,
        "handler":     None,
        "params":      {"app": "str"},
        "examples":    ["open notepad", "chrome kholo", "VS Code start karo"],
    },
    {
        "name":        "system_control",
        "description": "Shutdown, restart, or perform system-level power operations",
        "category":    "system",
        "enabled":     True,
        "handler":     None,
        "params":      {"action": "str", "delay": "int"},
        "examples":    ["shutdown", "restart", "pc band karo"],
    },
    {
        "name":        "get_time",
        "description": "Get the current date and time",
        "category":    "system",
        "enabled":     True,
        "handler":     None,
        "params":      {},
        "examples":    ["what time is it", "kitne baje hain"],
    },
    {
        "name":        "get_profile",
        "description": "Retrieve the owner's profile information",
        "category":    "system",
        "enabled":     True,
        "handler":     None,
        "params":      {},
        "examples":    ["my profile", "mera profile batao", "who am i"],
    },
    {
        "name":        "automation",
        "description": "Desktop automation — click, type, scroll using PyAutoGUI",
        "category":    "system",
        "enabled":     True,
        "handler":     None,
        "params":      {"task": "str"},
        "examples":    ["click", "scroll down", "type hello"],
    },

    # ── Browser Tools ─────────────────────────────────────────────────────────
    {
        "name":        "browser_navigate",
        "description": "Open a URL in the browser (Playwright-powered)",
        "category":    "browser",
        "enabled":     True,
        "handler":     None,
        "params":      {"url": "str"},
        "examples":    ["open linkedin.com", "go to github.com"],
    },
    {
        "name":        "browser_search",
        "description": "Search Google via browser and return results",
        "category":    "browser",
        "enabled":     True,
        "handler":     None,
        "params":      {"query": "str"},
        "examples":    ["search Java developer jobs", "google Spring Boot tutorial"],
    },
    {
        "name":        "browser_linkedin",
        "description": "Search LinkedIn for jobs, people, or companies",
        "category":    "browser",
        "enabled":     True,
        "handler":     None,
        "params":      {"query": "str", "location": "str"},
        "examples":    ["search HR Ahmedabad on LinkedIn", "find Java developer jobs"],
    },
    {
        "name":        "browser_extract",
        "description": "Extract and read text content from the current browser page",
        "category":    "browser",
        "enabled":     True,
        "handler":     None,
        "params":      {"selector": "str"},
        "examples":    ["read this page", "extract the article text"],
    },

    # ── Internet / Web Search ─────────────────────────────────────────────────
    {
        "name":        "internet_search",
        "description": "Fast DuckDuckGo text search (no browser needed)",
        "category":    "browser",
        "enabled":     True,
        "handler":     None,
        "params":      {"query": "str"},
        "examples":    ["search Python tutorials", "what is machine learning"],
    },

    # ── Memory Tools ──────────────────────────────────────────────────────────
    {
        "name":        "memory_remember",
        "description": "Store a fact, preference, or project detail in long-term memory",
        "category":    "memory",
        "enabled":     True,
        "handler":     None,
        "params":      {"text": "str", "category": "str"},
        "examples":    ["remember my Spring Boot project", "yaad rakh mera project"],
    },
    {
        "name":        "memory_search",
        "description": "Semantic search over stored long-term memories (FAISS)",
        "category":    "memory",
        "enabled":     True,
        "handler":     None,
        "params":      {"query": "str", "top_k": "int"},
        "examples":    ["do you remember my project", "kya yaad hai mujhe"],
    },

    # ── Mobile Tools ──────────────────────────────────────────────────────────
    {
        "name":        "mobile_control",
        "description": "Open an app on the connected Android device via ADB",
        "category":    "mobile",
        "enabled":     True,
        "handler":     None,
        "params":      {"package": "str"},
        "examples":    ["open WhatsApp on phone", "mobile pe chrome kholo"],
    },
    {
        "name":        "mobile_call",
        "description": "Make a phone call via the connected Android device",
        "category":    "mobile",
        "enabled":     True,
        "handler":     None,
        "params":      {"number": "str"},
        "examples":    ["call 9318302850", "phone karo mummy ko"],
    },
    {
        "name":        "mobile_alarm",
        "description": "Set an alarm on the connected Android device",
        "category":    "mobile",
        "enabled":     True,
        "handler":     None,
        "params":      {"hour": "str", "minute": "str"},
        "examples":    ["set alarm 7am", "7 baje alarm laga do"],
    },

    # ── Vision Tools ──────────────────────────────────────────────────────────
    {
        "name":        "vision_capture",
        "description": "Capture a camera frame or screenshot",
        "category":    "vision",
        "enabled":     True,
        "handler":     None,
        "params":      {},
        "examples":    ["take screenshot", "camera se photo lo"],
    },
    {
        "name":        "vision_detect",
        "description": "Detect objects or read text in captured image using OpenCV",
        "category":    "vision",
        "enabled":     True,
        "handler":     None,
        "params":      {"image_path": "str"},
        "examples":    ["what do you see", "detect objects in camera"],
    },

    # ── Phase-2 Reasoning Tools ───────────────────────────────────────────────
    {
        "name":        "reason_task",
        "description": "Run the ReasoningEngine on a task — extracts goal, risk, required tools, and reasoning steps",
        "category":    "reasoning",
        "enabled":     True,
        "handler":     None,
        "params":      {"task": "str"},
        "examples":    ["reason about this task", "analyse the goal", "what tools do I need"],
    },
    {
        "name":        "validate_task",
        "description": "Validate a set of execution results against expected goals using the Validator",
        "category":    "reasoning",
        "enabled":     True,
        "handler":     None,
        "params":      {"results": "list"},
        "examples":    ["validate results", "check if task succeeded", "verify execution"],
    },
    {
        "name":        "replan_task",
        "description": "Trigger auto-replan when a task fails — generates a new execution plan",
        "category":    "reasoning",
        "enabled":     True,
        "handler":     None,
        "params":      {"task": "str", "reason": "str"},
        "examples":    ["replan this task", "try again with different approach", "retry after failure"],
    },
    # ── Phase-3 Coding Tools ──────────────────────────────────────────────────
    {
        "name":        "generate_code",
        "description": "Generate source code from natural language prompt",
        "category":    "coding",
        "enabled":     True,
        "handler":     None,
        "params":      {"prompt": "str", "language": "str"},
        "examples":    ["create spring boot crud", "generate angular login component", "write python script for search"],
    },
    {
        "name":        "debug_code",
        "description": "Analyze errors, logs or exceptions and recommend code fixes",
        "category":    "coding",
        "enabled":     True,
        "handler":     None,
        "params":      {"logs": "str"},
        "examples":    ["debug this error", "fix NullPointerException in logs", "analyze javascript crash logs"],
    },
    {
        "name":        "analyze_stacktrace",
        "description": "Parse java/javascript/python stack trace to find offending class, method, line and issue description",
        "category":    "coding",
        "enabled":     True,
        "handler":     None,
        "params":      {"trace": "str"},
        "examples":    ["parse stack trace", "analyze java crash trace", "extract class and line from stack trace"],
    },
    {
        "name":        "generate_project",
        "description": "Generate complete boilerplate project structural folders, configuration files, Dockerfiles and READMEs",
        "category":    "coding",
        "enabled":     True,
        "handler":     None,
        "params":      {"project_type": "str", "name": "str", "description": "str"},
        "examples":    ["generate spring boot project", "create angular workspace", "generate node express dockerized project"],
    },
    {
        "name":        "refactor_code",
        "description": "Optimize source code structures, naming scopes, loop complexities or legacy patterns",
        "category":    "coding",
        "enabled":     True,
        "handler":     None,
        "params":      {"code": "str"},
        "examples":    ["refactor this code", "optimize java loop", "convert javascript var to const"],
    },
    {
        "name":        "generate_tests",
        "description": "Generate automated positive, negative and edge case unit test classes",
        "category":    "coding",
        "enabled":     True,
        "handler":     None,
        "params":      {"code": "str", "framework": "str"},
        "examples":    ["generate junit test cases", "create pytest functions for python script", "generate jest tests"],
    },
    {
        "name":        "explain_code",
        "description": "Provide a high-level summary and line-by-line detailed functional explanation of source code",
        "category":    "coding",
        "enabled":     True,
        "handler":     None,
        "params":      {"code": "str"},
        "examples":    ["explain this code block", "what does this code do line by line", "provide java service explanation"],
    },
    {
        "name":        "review_code",
        "description": "Perform automated review of security violations, performance bottlenecks and SOLID violations in source code",
        "category":    "coding",
        "enabled":     True,
        "handler":     None,
        "params":      {"code": "str"},
        "examples":    ["review this code", "analyze code quality and security", "check solid principles in class"],
    },
]


class ToolRegistry:
    """
    Dynamic registry of all MSA Agent tools.

    Tools can be:
    - Queried by name or category
    - Enabled/disabled individually or by feature flag
    - Extended at runtime via register()
    - Executed directly via execute()
    """

    def __init__(self):
        self._tools: Dict[str, Dict] = {}
        self._load_defaults()
        self._apply_config_flags()
        logger.info(
            "ToolRegistry initialized: %d tools (%d enabled).",
            len(self._tools),
            len(self.list_enabled()),
        )

    # ── Init ──────────────────────────────────────────────────────────────────

    def _load_defaults(self) -> None:
        """Load the built-in tool definitions."""
        for tool in _DEFAULT_TOOLS:
            self._tools[tool["name"]] = dict(tool)

    def _apply_config_flags(self) -> None:
        """Disable tool categories based on config feature flags."""
        try:
            from config import (
                ENABLE_BROWSER_AGENT,
                ENABLE_RAG_MEMORY,
            )
            if not ENABLE_BROWSER_AGENT:
                for name, t in self._tools.items():
                    if t["category"] == "browser" and name != "internet_search":
                        t["enabled"] = False
                logger.info("Browser agent disabled by config.")

            if not ENABLE_RAG_MEMORY:
                for name, t in self._tools.items():
                    if t["category"] == "memory":
                        t["enabled"] = False
                logger.info("RAG memory tools disabled by config.")

            from config import ENABLE_CODING_AGENT
            if not ENABLE_CODING_AGENT:
                for name, t in self._tools.items():
                    if t["category"] == "coding":
                        t["enabled"] = False
                logger.info("Coding tools disabled by config.")

        except ImportError:
            pass  # config not available — keep all enabled

    # ── Public API ────────────────────────────────────────────────────────────

    def register(self, tool_def: Dict) -> None:
        """
        Register a new tool or update an existing one.

        Args:
            tool_def: Dict with keys: name, description, category,
                      enabled, handler, params, examples.
        """
        name = tool_def.get("name")
        if not name:
            raise ValueError("Tool definition must have a 'name' field.")
        self._tools[name] = tool_def
        logger.info("ToolRegistry: registered tool '%s'.", name)

    def set_handler(self, name: str, handler: Callable) -> None:
        """Attach an executable handler function to a registered tool."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found in registry.")
        self._tools[name]["handler"] = handler
        logger.debug("ToolRegistry: handler set for '%s'.", name)

    def get(self, name: str) -> Optional[Dict]:
        """Retrieve a tool definition by name."""
        return self._tools.get(name)

    def list_enabled(self) -> List[str]:
        """Return names of all enabled tools."""
        return [n for n, t in self._tools.items() if t.get("enabled", True)]

    def list_all(self) -> List[Dict]:
        """Return all tool definitions (enabled and disabled)."""
        return list(self._tools.values())

    def list_by_category(self, category: str) -> List[Dict]:
        """Return enabled tools for a given category."""
        return [
            t for t in self._tools.values()
            if t.get("category") == category and t.get("enabled", True)
        ]

    def enable(self, name: str) -> None:
        """Enable a specific tool."""
        if name in self._tools:
            self._tools[name]["enabled"] = True

    def disable(self, name: str) -> None:
        """Disable a specific tool."""
        if name in self._tools:
            self._tools[name]["enabled"] = False

    def execute(self, name: str, params: Dict[str, Any]) -> str:
        """
        Execute a tool by name with given parameters.

        Args:
            name:   Tool name.
            params: Parameters dict matching the tool's param schema.

        Returns:
            Result string from the tool handler.
        """
        tool = self._tools.get(name)
        if not tool:
            return f"Tool '{name}' not found in registry."
        if not tool.get("enabled", True):
            return f"Tool '{name}' is currently disabled."

        handler = tool.get("handler")
        if handler is None:
            return f"Tool '{name}' has no handler attached yet."

        try:
            result = handler(params)
            logger.info("ToolRegistry: executed '%s' → %r", name, str(result)[:80])
            return str(result)
        except Exception as e:
            logger.error("ToolRegistry: '%s' execution error: %s", name, e)
            return f"Tool '{name}' failed: {e}"

    def suggest_tool(self, intent: str) -> Optional[str]:
        """
        Map an intent string to the best matching tool name.

        Args:
            intent: Intent label from LanguageManager / DecisionEngine.

        Returns:
            Tool name string, or None if no match.
        """
        intent_to_tool = {
            "open_app":          "open_app",
            "close_app":         "open_app",
            "shutdown":          "system_control",
            "restart":           "system_control",
            "get_time":          "get_time",
            "get_profile":       "get_profile",
            "automation":        "automation",
            "internet_search":   "internet_search",
            "browser_search":    "browser_search",
            "browser_navigate":  "browser_navigate",
            "mobile_make_call":  "mobile_call",
            "mobile_set_alarm":  "mobile_alarm",
            "mobile_open_app":   "mobile_control",
            "memory_remember":   "memory_remember",
            "memory_recall":     "memory_search",
            "vision":            "vision_capture",
            "location":          "get_profile",
            # Phase-2 reasoning intents
            "reason_task":       "reason_task",
            "validate_task":     "validate_task",
            "replan_task":       "replan_task",
            "reasoning":         "reason_task",
            "validate":          "validate_task",
            "replan":            "replan_task",
            # Phase-3 coding intents
            "code_generation":   "generate_code",
            "debugging":         "debug_code",
            "project_creation":  "generate_project",
            "code_review":       "review_code",
            "test_generation":   "generate_tests",
            "explain_code":      "explain_code",
            "refactor_code":     "refactor_code",
            "analyze_stacktrace":"analyze_stacktrace",
        }
        tool_name = intent_to_tool.get(intent)
        if tool_name and self._tools.get(tool_name, {}).get("enabled", True):
            return tool_name
        return None

    def to_dict(self) -> Dict:
        """Serialize registry to JSON-safe dict for API responses."""
        return {
            name: {
                "description": t["description"],
                "category":    t["category"],
                "enabled":     t.get("enabled", True),
                "params":      t.get("params", {}),
                "examples":    t.get("examples", []),
            }
            for name, t in self._tools.items()
        }


# ── Module-level singleton ────────────────────────────────────────────────────
registry = ToolRegistry()
