"""
agent/reflection.py
====================
Provides self-critique and output reflection pass.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger("msa.reflection")

_REFLECT_MODES = {"deep_thinking", "research", "architect", "autonomous", "coding", "debug"}


class ReflectionEngine:
    def __init__(self, llm_manager):
        self.llm = llm_manager

    def maybe_reflect(self, original_question: str, draft_answer: str, mode: str = "balanced") -> str:
        """Only runs the extra reflection pass for modes where quality matters more than speed."""
        if mode not in _REFLECT_MODES or not draft_answer:
            return draft_answer

        critique_prompt = (
            f"Question: {original_question}\n\n"
            f"Draft answer: {draft_answer}\n\n"
            f"Check this answer for: factual errors, logical gaps, missing edge "
            f"cases, or incomplete code. If it's correct and complete, output it "
            f"unchanged. If it has issues, output the corrected/improved version. "
            f"Output ONLY the final answer, no meta-commentary about what you changed."
        )
        try:
            improved = self.llm.generate(critique_prompt, provider="ollama")
            return improved or draft_answer
        except Exception as e:
            logger.warning("Reflection pass failed, keeping draft answer: %s", e)
            return draft_answer
