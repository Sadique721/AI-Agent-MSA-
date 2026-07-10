"""
agent/swarm.py
===============
Lightweight multi-role swarm: routes a single objective through specialized
"role" prompts (Planner -> Architect -> Coder -> Security reviewer) using the
SAME LLMManager instance the rest of the app already uses. This does not
replace AgentService — it's an additional capability AgentService can call
for complex, multi-step objectives (e.g. "build a full CRUD module").
"""
import logging
from typing import Dict, Any

logger = logging.getLogger("msa.swarm")


class SwarmCoordinator:
    def __init__(self, llm_manager):
        self.llm = llm_manager
        self.roles = ["Planner", "Architect", "Coder", "SecurityReviewer"]

    def orchestrate_task(self, objective: str) -> Dict[str, Any]:
        logger.info("Swarm: starting objective: %s", objective)
        plan = self._invoke_role("Planner",
            f"Break this objective into a numbered task list: {objective}")
        arch = self._invoke_role("Architect",
            f"Design the structure/files needed for this plan:\n{plan}")
        code = self._invoke_role("Coder",
            f"Write the complete implementation for this design:\n{arch}")
        audit = self._invoke_role("SecurityReviewer",
            f"Review this code for security issues, bugs, and missing error handling:\n{code}")

        return {
            "status": "completed",
            "plan": plan,
            "architecture": arch,
            "artifact": code,
            "review": audit,
        }

    def _invoke_role(self, role: str, instruction: str) -> str:
        prompt = f"You are acting as: {role}.\n\n{instruction}"
        return self.llm.generate(prompt, provider="ollama") or ""
