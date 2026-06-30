"""
agent/ReasoningEngine.py
========================
Phase-2: Reasoning-Based Autonomous Agent core.

ReasoningEngine analyses every user request BEFORE the Planner acts.
It produces a structured 'reasoning packet' that drives smarter planning,
context-aware validation, and auto-replanning on failure.

Reasoning Types
---------------
  system      — OS-level: open app, time, profile, shutdown
  browser     — Web browsing, search, LinkedIn, scraping
  coding      — Code writing, editing, file operations
  memory      — Store/recall facts, semantic search
  mobile      — Phone calls, SMS, alarms, mobile apps
  automation  — Desktop automation, GUI scripting

Risk Levels
-----------
  low    — read-only or informational actions
  medium — write/navigate to unknown URLs, file operations
  high   — destructive or sensitive: shutdown, call, SMS, delete, login
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("msa.agent.reasoning")

# ── High-risk keywords that require explicit user approval ────────────────────
_HIGH_RISK_KEYWORDS = [
    "shutdown", "restart", "delete", "remove", "format",
    "phone call", "dial number", "make a call",
    "send sms", "send message", "send whatsapp",
    "login", "log in", "sign in", "password",
    "factory reset",
    "call", "sms",
]

_MEDIUM_RISK_KEYWORDS = [
    "navigate to", "open url", "go to", "open website",
    "write file", "create file", "edit file",
    "install", "uninstall", "download",
    "send email",
]

# ── Tool requirement keyword maps ─────────────────────────────────────────────
_TOOL_KEYWORDS: Dict[str, List[str]] = {
    "browser_linkedin": ["linkedin", "job", "jobs", "career", "hiring", "hr", "recruiter"],
    "browser_search":   ["google", "search", "find online", "look up", "web search"],
    "browser_navigate": ["open url", "navigate to", "go to", "website", "http"],
    "browser_extract":  ["extract", "read page", "scrape", "get text", "parse"],
    "internet_search":  ["search", "find", "what is", "how to", "tell me about"],
    "memory_remember":  ["remember", "save", "store", "yaad rakh", "note"],
    "memory_search":    ["recall", "do you remember", "what did", "kya yaad"],
    "open_app":         ["open", "start", "launch", "kholo", "chalao", "notepad", "chrome", "vscode"],
    "system_control":   ["shutdown", "restart", "power off", "band karo"],
    "get_time":         ["time", "date", "clock", "kitne baje"],
    "get_profile":      ["profile", "who am i", "mera naam", "about me"],
    "mobile_call":      ["call", "dial", "phone", "ring"],
    "mobile_alarm":     ["alarm", "wake up", "remind", "alert"],
    "mobile_control":   ["mobile", "android", "phone app", "whatsapp", "phone mein"],
    "automation":       ["click", "type", "scroll", "automate", "desktop"],
    "vision_capture":   ["screenshot", "photo", "camera", "capture", "see"],
    "generate_code":    ["generate code", "write code", "create spring boot", "create crud", "generate angular", "generate sql", "write python"],
    "debug_code":       ["debug", "fix error", "runtime error", "exception in", "crash"],
    "analyze_stacktrace":["stacktrace", "stack trace", "exception trace", "at java.", "at customer"],
    "generate_project": ["project", "boilerplate", "pom.xml", "package.json", "dockerfile", "docker-compose"],
    "refactor_code":    ["refactor", "optimize", "clean code", "reduce complexity", "modernize"],
    "generate_tests":   ["test", "tests", "unit test", "pytest", "junit", "jest"],
    "explain_code":     ["explain", "what does", "line by line", "breakdown"],
    "review_code":      ["review", "code quality", "security check", "solid principles", "code check"],
}

# ── Reasoning type keyword maps ───────────────────────────────────────────────
_REASONING_TYPE_MAP: Dict[str, List[str]] = {
    "browser":    ["linkedin", "google", "search", "web", "url", "website", "scrape",
                   "extract", "jobs", "browse", "navigate", "http"],
    "mobile":     ["call", "sms", "alarm", "mobile", "android", "phone", "whatsapp",
                   "notification", "dial"],
    "coding":     ["code", "python", "java", "html", "react", "vscode", "file",
                   "write", "program", "script", "function", "class", "crud", "stacktrace",
                   "debug", "refactor", "test", "explain", "review", "bug", "exception"],
    "memory":     ["remember", "recall", "store", "yaad", "forget", "history",
                   "memory", "save", "past"],
    "automation": ["click", "scroll", "type", "automate", "gui", "desktop",
                   "keyboard", "mouse", "button"],
    "system":     ["time", "date", "profile", "shutdown", "restart", "open",
                   "notepad", "chrome", "launch", "app", "power",
                   "show my", "display", "who am i", "mera", "about me"],
}

# ── Dependency keyword maps ───────────────────────────────────────────────────
_DEPENDENCY_MAP: Dict[str, List[str]] = {
    "internet":  ["search", "linkedin", "google", "web", "url", "online", "website"],
    "browser":   ["linkedin", "navigate", "chrome", "browser", "url", "http"],
    "microphone":["voice", "speak", "listen", "record", "audio"],
    "camera":    ["photo", "screenshot", "capture", "vision", "see"],
    "storage":   ["file", "write", "save", "store", "download", "code", "project"],
    "phone":     ["call", "dial", "sms", "mobile", "android", "alarm"],
    "location":  ["gps", "location", "map", "where am i", "nearby"],
}


class ReasoningEngine:
    """
    MSA Phase-2 Reasoning Engine.

    Transforms raw user input into a structured reasoning packet that guides
    the Planner and Validator for autonomous, context-aware task execution.
    """

    def __init__(self):
        self._llm = None
        self._load_llm()
        logger.info("ReasoningEngine initialised.")

    def _load_llm(self) -> None:
        """Optionally load LLaMA/DeepSeek for LLM-assisted reasoning."""
        import os
        from config import PROJECT_ROOT
        paths = [
            os.path.join(PROJECT_ROOT, "models", "llm", "deepseek.gguf"),
            os.path.join(PROJECT_ROOT, "models", "llm", "llama-2-7b-chat.Q4_K_M.gguf"),
        ]
        for path in paths:
            if os.path.exists(path):
                try:
                    from llama_cpp import Llama
                    self._llm = Llama(model_path=path, n_ctx=2048, verbose=False)
                    logger.info("ReasoningEngine: LLM loaded from %s", path)
                    return
                except ImportError:
                    logger.info("llama-cpp-python not installed. Rule-based reasoning only.")
                except Exception as e:
                    logger.warning("LLM load failed: %s", e)
        logger.info("ReasoningEngine: no LLM found, rule-based reasoning active.")

    # ── Public API ────────────────────────────────────────────────────────────

    def reason(
        self,
        user_input: str,
        context: Optional[List] = None,
        failure_hint: Optional[Dict] = None,
        replan_attempt: int = 0,
    ) -> Dict[str, Any]:
        """
        Analyse user input and produce a reasoning packet.

        Args:
            user_input:   Raw user command (English / Hinglish).
            context:      Recent conversation context (list of strings).
            failure_hint: On replan, the Validator failure dict from previous attempt.
            replan_attempt: Current replan retry attempt count.

        Returns:
            {
              "goal":              str,
              "reasoning_type":    str,   # system|browser|coding|memory|mobile|automation
              "required_tools":    list,
              "risk_level":        str,   # low|medium|high
              "requires_approval": bool,
              "dependencies":      list,
              "reasoning_steps":   list,
              "replan_attempt":    int,
              "failure_hint":      dict | None,
            }
        """
        if not user_input or not user_input.strip():
            return self._empty_packet()

        context = context or []
        lower = user_input.lower().strip()

        # Try LLM-assisted reasoning first
        if self._llm:
            result = self._llm_reason(user_input, context)
            if result:
                result["replan_attempt"] = replan_attempt
                result["failure_hint"] = failure_hint
                return result

        # Fall back to rule-based reasoning
        packet = self._rule_based_reason(lower, user_input, context)
        packet["replan_attempt"] = replan_attempt
        packet["failure_hint"] = failure_hint

        if failure_hint:
            logger.info(
                "ReasoningEngine: replanning due to failure — %s",
                failure_hint.get("reason", "unknown"),
            )
            packet = self._adjust_for_replan(packet, failure_hint)

        logger.info(
            "ReasoningEngine: goal='%s' type=%s risk=%s tools=%s",
            packet["goal"],
            packet["reasoning_type"],
            packet["risk_level"],
            packet["required_tools"],
        )
        return packet

    def get_reasoning_type(self, user_input: str) -> str:
        """Classify input into one of 6 reasoning types."""
        lower = user_input.lower()
        scores: Dict[str, int] = {t: 0 for t in _REASONING_TYPE_MAP}
        for rtype, keywords in _REASONING_TYPE_MAP.items():
            for kw in keywords:
                if kw in lower:
                    scores[rtype] += 1
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "system"

    def detect_risk(self, user_input: str) -> str:
        """Return risk level: 'low' | 'medium' | 'high'."""
        lower = user_input.lower()
        for kw in _HIGH_RISK_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", lower):
                return "high"
        for kw in _MEDIUM_RISK_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", lower):
                return "medium"
        return "low"

    def requires_approval(self, user_input: str) -> bool:
        """Return True if action needs explicit user confirmation."""
        import os
        if os.environ.get("MSA_AUTO_APPROVE", "false").lower() == "true":
            return False
        return self.detect_risk(user_input) == "high"

    def extract_goal(self, user_input: str) -> str:
        """Extract a concise goal description from user input."""
        # Remove filler words
        fillers = [
            r"\bplease\b", r"\bkindly\b", r"\bcan you\b", r"\bcould you\b",
            r"\bwould you\b", r"\bhelp me\b", r"\bzara\b", r"\bplz\b",
        ]
        goal = user_input.strip()
        for filler in fillers:
            goal = re.sub(filler, "", goal, flags=re.IGNORECASE).strip()
        # Capitalise first letter
        return goal[:1].upper() + goal[1:] if goal else user_input

    def detect_required_tools(self, user_input: str) -> List[str]:
        """Return ordered list of tool names likely needed for this task."""
        lower = user_input.lower()
        tools: List[str] = []
        for tool_name, keywords in _TOOL_KEYWORDS.items():
            for kw in keywords:
                if kw in lower and tool_name not in tools:
                    tools.append(tool_name)
                    break
        # Always include memory_remember for save-type tasks
        if any(w in lower for w in ["save", "store", "keep", "remember", "note"]):
            if "memory_remember" not in tools:
                tools.append("memory_remember")
        return tools if tools else ["internet_search"]

    def detect_dependencies(self, user_input: str) -> List[str]:
        """Return list of system/hardware dependencies."""
        lower = user_input.lower()
        deps: List[str] = []
        for dep, keywords in _DEPENDENCY_MAP.items():
            for kw in keywords:
                if kw in lower and dep not in deps:
                    deps.append(dep)
                    break
        return deps if deps else ["none"]

    def build_reasoning_steps(
        self, goal: str, tools: List[str], reasoning_type: str
    ) -> List[str]:
        """Generate human-readable reasoning steps for the plan."""
        steps: List[str] = []

        type_step_map = {
            "browser":    "Open browser and navigate to relevant page",
            "mobile":     "Connect to mobile device and verify readiness",
            "coding":     "Prepare code editor or file environment",
            "memory":     "Search existing memory for relevant context",
            "automation": "Identify target UI element for automation",
            "system":     "Check system state before execution",
        }
        if reasoning_type in type_step_map:
            steps.append(type_step_map[reasoning_type])

        for tool in tools:
            tool_step_map = {
                "browser_linkedin": "Search LinkedIn for matching results",
                "browser_search":   "Execute Google search query",
                "browser_navigate": "Navigate browser to target URL",
                "browser_extract":  "Extract and parse page content",
                "internet_search":  "Perform DuckDuckGo text search",
                "memory_remember":  "Store results in long-term memory",
                "memory_search":    "Recall relevant past memories",
                "open_app":         "Launch target application",
                "system_control":   "Execute system-level command",
                "get_time":         "Fetch current system time",
                "get_profile":      "Retrieve user profile data",
                "mobile_call":      "Initiate phone call via ADB",
                "mobile_alarm":     "Set alarm on connected device",
                "mobile_control":   "Open app on mobile device",
                "automation":       "Execute desktop automation script",
                "vision_capture":   "Capture screenshot or camera frame",
                "generate_code":    "Generate source code based on description",
                "debug_code":       "Analyze runtime logs or exceptions to isolate the bug",
                "analyze_stacktrace":"Parse error stack trace coordinates to locate error line",
                "generate_project": "Generate full project directories and config blueprints",
                "refactor_code":    "Refactor legacy structures into clean code implementation",
                "generate_tests":   "Generate unit test cases covering positive/negative/edge cases",
                "explain_code":     "Explain source code block structure line-by-line",
                "review_code":      "Perform static code analysis to review quality and SOLID design",
            }
            if tool in tool_step_map:
                step = tool_step_map[tool]
                if step not in steps:
                    steps.append(step)

        steps.append("Validate execution results")
        steps.append(f"Store outcome in memory for goal: {goal[:60]}")
        return steps

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _rule_based_reason(
        self, lower: str, user_input: str, context: List
    ) -> Dict[str, Any]:
        goal = self.extract_goal(user_input)
        reasoning_type = self.get_reasoning_type(lower)
        risk_level = self.detect_risk(lower)
        needs_approval = self.requires_approval(lower)
        required_tools = self.detect_required_tools(lower)
        dependencies = self.detect_dependencies(lower)
        reasoning_steps = self.build_reasoning_steps(goal, required_tools, reasoning_type)

        return {
            "goal":              goal,
            "reasoning_type":    reasoning_type,
            "required_tools":    required_tools,
            "risk_level":        risk_level,
            "requires_approval": needs_approval,
            "dependencies":      dependencies,
            "reasoning_steps":   reasoning_steps,
        }

    def _llm_reason(
        self, user_input: str, context: List
    ) -> Optional[Dict[str, Any]]:
        """Ask LLM to produce a reasoning packet as JSON."""
        prompt = f"""You are MSA ReasoningEngine. Analyse this user request and return a JSON reasoning packet.

User Request: {user_input}
Context: {context[-3:] if context else []}

Respond ONLY with valid JSON:
{{
  "goal": "concise goal description",
  "reasoning_type": "system|browser|coding|memory|mobile|automation",
  "required_tools": ["tool1", "tool2"],
  "risk_level": "low|medium|high",
  "requires_approval": false,
  "dependencies": ["dep1"],
  "reasoning_steps": ["step 1", "step 2", "step 3"]
}}"""
        try:
            import json
            output = self._llm(prompt, max_tokens=400, temperature=0.1, stop=["```"])
            text = output["choices"][0]["text"].strip()
            start, end = text.find("{"), text.rfind("}") + 1
            if 0 <= start < end:
                return json.loads(text[start:end])
        except Exception as e:
            logger.warning("LLM reasoning failed: %s", e)
        return None

    def _adjust_for_replan(
        self, packet: Dict[str, Any], failure_hint: Dict
    ) -> Dict[str, Any]:
        """Adjust reasoning packet to avoid repeating a known failure."""
        failed_tools = failure_hint.get("failed_steps", [])
        failed_names = [s.get("tool") for s in failed_tools if isinstance(s, dict)]

        # Remove failed tools and add fallbacks
        packet["required_tools"] = [
            t for t in packet["required_tools"] if t not in failed_names
        ]
        # Add fallback if browser failed → try internet_search instead
        if any("browser" in str(t) for t in failed_names):
            if "internet_search" not in packet["required_tools"]:
                packet["required_tools"].insert(0, "internet_search")

        packet["reasoning_steps"].insert(0, f"Previous attempt failed: {failure_hint.get('reason', 'unknown error')}. Adjusting strategy.")
        return packet

    def _empty_packet(self) -> Dict[str, Any]:
        return {
            "goal":              "No input provided",
            "reasoning_type":    "system",
            "required_tools":    [],
            "risk_level":        "low",
            "requires_approval": False,
            "dependencies":      [],
            "reasoning_steps":   [],
            "replan_attempt":    0,
            "failure_hint":      None,
        }
