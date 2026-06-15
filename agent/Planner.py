"""
agent/Planner.py
================
Multi-step Planner Agent for breaking complex queries into sequential tasks.
Supports both LLM-assisted generation and high-quality Hinglish-aware rule fallbacks.
"""

import logging
import re
import json
from typing import List, Dict, Any, Optional
from tools.tool_registry import registry
from language.language_manager import LanguageManager

logger = logging.getLogger("msa.agent.planner")

# Planning delimiters to split complex multi-step queries
DELIMITERS = [
    r"\band then\b",
    r"\band after\b",
    r"\baur phir\b",
    r"\bphir\b",
    r"\bthen\b",
    r"\band then\b"
]
_DELIM_RE = re.compile("|".join(DELIMITERS), re.IGNORECASE)


class PlannerAgent:
    """
    Planner Agent that generates sequential execution plans.
    Uses LLM if model files are found, else falls back to LanguageManager-based routing.
    """

    def __init__(self, language_manager: Optional[LanguageManager] = None):
        self.language_manager = language_manager or LanguageManager()
        self._llm = None
        self._load_llm()

    def _load_llm(self) -> None:
        """Attempt to lazily load LLaMA or DeepSeek model for planning."""
        from config import PROJECT_ROOT
        import os
        paths = [
            os.path.join(PROJECT_ROOT, "models", "llm", "llama-2-7b-chat.Q4_K_M.gguf"),
            os.path.join(PROJECT_ROOT, "models", "llm", "deepseek.gguf")
        ]
        for path in paths:
            if os.path.exists(path):
                try:
                    from llama_cpp import Llama
                    self._llm = Llama(model_path=path, n_ctx=2048, verbose=False)
                    logger.info("PlannerAgent: loaded LLM from %s", path)
                    break
                except ImportError:
                    logger.info("llama-cpp-python not installed. Planner LLM disabled.")
                except Exception as e:
                    logger.warning("PlannerAgent LLM load error: %s", e)

    def get_task_category(self, user_input: str) -> str:
        """Categorize the user query for analytics and system optimization."""
        lower = user_input.lower()
        if any(w in lower for w in ["code", "python", "java", "react", "html", "vscode", "programming", "file", "write"]):
            return "coding_task"
        if any(w in lower for w in ["linkedin", "google", "youtube", "search", "web", "url", "website", "browser", "link", "scrape"]):
            return "browser_task"
        if any(w in lower for w in ["mobile", "call", "phone", "dial", "alarm", "android", "device"]):
            return "mobile_task"
        return "system_task"

    def plan(self, user_input: str, context: Optional[List] = None) -> List[Dict[str, Any]]:
        """
        Generate a list of plan steps for the user task.
        Each step conforms to:
        {
           "step": int,
           "tool": str,
           "action": str,
           "params": dict
        }
        """
        if self._llm:
            plan_res = self._llm_plan(user_input, context)
            if plan_res:
                return plan_res

        return self._rule_based_plan(user_input)

    def _llm_plan(self, user_input: str, context: Optional[List]) -> Optional[List[Dict[str, Any]]]:
        """Ask LLM to structure the task."""
        tools_summary = ""
        for t in registry.list_all():
            if t.get("enabled", True):
                tools_summary += f"- {t['name']}: {t['description']} (params: {list(t['params'].keys())})\n"

        prompt = f"""You are the MSA Planner Agent. Break down the user's task into sequential steps using these tools:
{tools_summary}
User Task: {user_input}
Context: {context}

Respond ONLY with a JSON array of steps:
[
  {{"step": 1, "tool": "tool_name", "action": "action_name", "params": {{...}}}}
]"""
        try:
            output = self._llm(prompt, max_tokens=512, temperature=0.2, stop=["\n\n"])
            text = output["choices"][0]["text"].strip()
            start = text.find("[")
            end = text.rfind("]") + 1
            if 0 <= start < end:
                steps = json.loads(text[start:end])
                for idx, s in enumerate(steps):
                    s.setdefault("step", idx + 1)
                    s.setdefault("tool", "none")
                    s.setdefault("action", "none")
                    s.setdefault("params", {})
                return steps
        except Exception as e:
            logger.error("PlannerAgent LLM plan failed: %s", e)
        return None

    def _rule_based_plan(self, user_input: str) -> List[Dict[str, Any]]:
        """Splits multi-step commands by conjunctions and matches intents via LanguageManager."""
        sub_commands = [c.strip() for c in _DELIM_RE.split(user_input) if c.strip()]
        steps = []

        for idx, cmd in enumerate(sub_commands):
            lang_res = self.language_manager.process(cmd)
            intent = lang_res.get("intent", "none")
            tool_name = registry.suggest_tool(intent)

            # Extract param keys
            params = {}
            for k, v in lang_res.items():
                if k not in ["intent", "language", "confidence", "response", "normalized", "detection"]:
                    params[k] = v

            # Fallback if no matching tool was suggested, but we have text
            if not tool_name:
                if intent == "none" or not intent:
                    # Treat unknown commands as browser/web search
                    tool_name = "internet_search"
                    params = {"query": cmd}
                else:
                    tool_name = "system_control"

            steps.append({
                "step": idx + 1,
                "tool": tool_name,
                "action": intent if intent and intent != "none" else tool_name,
                "params": params
            })

        return steps
